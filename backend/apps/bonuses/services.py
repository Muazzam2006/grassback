
from decimal import ROUND_HALF_UP, Decimal

from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models import F

from apps.orders.models import Order, OrderStatus

from .models import Bonus, BonusStatus, BonusType, CalculationType, MLMRule

User = get_user_model()

_QUANTIZE_STEP = Decimal("0.01")
_MAX_LEVELS = 20


def distribute_order_bonuses(order: Order) -> list[Bonus]:

    with transaction.atomic():
        order = (
            Order.objects
            .select_for_update()
            .select_related("user")
            .get(pk=order.pk)
        )

        if order.status != OrderStatus.DELIVERED:
            raise ValueError(
                f"Cannot distribute bonuses for order {order.pk!r}: "
                f"status is {order.status!r}, expected DELIVERED (COD)."
            )

        buyer = order.user

        ancestors = (
            buyer
            .get_ancestors(ascending=True)
            .only("id", "status")
            [:_MAX_LEVELS]
        )

        rule_map: dict[tuple[str, int], MLMRule] = {
            (r.agent_status, r.level): r
            for r in MLMRule.objects.filter(is_active=True, level__lte=_MAX_LEVELS)
        }

        created: list[Bonus] = []

        for mlm_level, ancestor in enumerate(ancestors, start=1):
            rule = rule_map.get((ancestor.status, mlm_level))
            if rule is None:
                continue

            # Calculate bonus amount based on rule type
            if rule.calculation_type == CalculationType.PERCENT:
                amount = (
                    order.total_amount * rule.value / Decimal("100")
                ).quantize(_QUANTIZE_STEP, rounding=ROUND_HALF_UP)
            else:  # FIXED
                amount = rule.value.quantize(_QUANTIZE_STEP, rounding=ROUND_HALF_UP)

            if amount <= Decimal("0.00"):
                continue

            bonus_type = BonusType.PERSONAL if mlm_level == 1 else BonusType.TEAM

            bonus, is_new = Bonus.objects.get_or_create(
                user=ancestor,
                order=order,
                level=mlm_level,
                bonus_type=bonus_type,
                defaults={
                    "source_user": buyer,
                    # v2 snapshots
                    "calculation_type_snapshot": rule.calculation_type,
                    "applied_value_snapshot": rule.value,
                    # v1 compat: null for FIXED bonuses
                    "percent_snapshot": (
                        rule.value if rule.calculation_type == CalculationType.PERCENT else None
                    ),
                    "amount": amount,
                    "status": BonusStatus.PENDING,
                },
            )

            if is_new:
                created.append(bonus)

        return created


@transaction.atomic
def confirm_order_bonuses(order: Order) -> int:
    """
    Promote all PENDING bonuses for *order* to CONFIRMED and credit user balances.

    Raises:
        ValueError: if *order* is not in DELIVERED status (guard against misuse).
    """
    # Re-read status from DB to avoid acting on a stale in-memory object.
    # OrderStatus is imported at the top of this module.
    fresh_status = Order.objects.filter(pk=order.pk).values_list("status", flat=True).first()
    if fresh_status != OrderStatus.DELIVERED:
        raise ValueError(
            f"Cannot confirm bonuses for order {order.pk!r}: "
            f"expected DELIVERED, got {fresh_status!r}."
        )

    pending_bonuses = list(
        Bonus.objects
        .select_for_update()
        .select_related("user")
        .filter(order=order, status=BonusStatus.PENDING)
    )

    if not pending_bonuses:
        return 0

    user_deltas: dict[int, dict] = {}
    for bonus in pending_bonuses:
        uid = bonus.user_id
        if uid not in user_deltas:
            user_deltas[uid] = {
                "personal_delta": Decimal("0.00"),
                "team_delta": Decimal("0.00"),
                "balance_delta": Decimal("0.00"),
            }
        d = user_deltas[uid]
        d["balance_delta"] += bonus.amount
        if bonus.bonus_type == BonusType.PERSONAL:
            d["personal_delta"] += bonus.amount
        else:
            d["team_delta"] += bonus.amount

    for uid, d in user_deltas.items():
        update_kwargs: dict = {"bonus_balance": F("bonus_balance") + d["balance_delta"]}
        if d["personal_delta"] > Decimal("0.00"):
            update_kwargs["personal_turnover"] = F("personal_turnover") + d["personal_delta"]
        if d["team_delta"] > Decimal("0.00"):
            update_kwargs["team_turnover"] = F("team_turnover") + d["team_delta"]
        User.objects.filter(pk=uid).update(**update_kwargs)

    Bonus.objects.filter(
        pk__in=[b.pk for b in pending_bonuses]
    ).update(status=BonusStatus.CONFIRMED)

    # Re-evaluate MLM status for all users whose turnover counters changed.
    from apps.mlm.services import promote_user_status

    for uid in user_deltas:
        locked_user = User.objects.select_for_update().get(pk=uid)
        promote_user_status(locked_user)

    return len(pending_bonuses)
