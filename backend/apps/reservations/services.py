
from decimal import Decimal

from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models import F, Sum
from django.utils import timezone

from apps.products.models import ProductVariant
from apps.orders.models import Order, OrderItem, OrderStatus
from apps.delivery.models import DeliveryAddress

from .models import Reservation, ReservationStatus

User = get_user_model()


_TIMEOUT_MINUTES: int = getattr(settings, "RESERVATION_TIMEOUT_MINUTES", 21600)  # 15 days
_MAX_DISTINCT_PRODUCTS_PER_USER = 3


class ReservationError(Exception):
    """Base class for all reservation-domain errors."""


class InsufficientStockError(ReservationError):
    """Raised when available stock is less than requested quantity."""


class DuplicateActiveReservationError(ReservationError):
    """Raised when user already has an ACTIVE reservation for the same variant."""


class ProductLimitExceededError(ReservationError):
    """Raised when user already has reservations on 3 distinct products."""


class ReservationNotActiveError(ReservationError):
    """Raised when a reservation is not in ACTIVE status."""


class ReservationExpiredError(ReservationError):
    """Raised when a reservation has passed its expires_at timestamp."""


class ReservationConversionError(ReservationError):
    """Raised when checkout cannot convert reservations (stock or status mismatch)."""


# ---------------------------------------------------------------------------
# Public service: create reservation
# ---------------------------------------------------------------------------

@transaction.atomic
def reserve_variant(
    user: User,
    variant: ProductVariant,
    quantity: int,
) -> Reservation:
    """
    Soft-reserve *quantity* units of *variant* for *user*.

    Steps:
        1. Validate quantity is positive.
        2. Acquire row-level lock on ProductVariant (select_for_update).
        3. Compute available = stock - SUM(active reservations).
        4. Guard: no existing ACTIVE (user, variant) reservation.
        5. Guard: user has fewer than 3 distinct products already reserved.
        6. Stock check: available >= quantity.
        7. INSERT Reservation row.

    Raises:
        ValueError: quantity is less than 1.
        DuplicateActiveReservationError: ACTIVE (user, variant) already exists.
        ProductLimitExceededError: user already has 3 distinct active products.
        InsufficientStockError: available stock < quantity.
    """
    # --- 1. Quantity lower bound ---
    if quantity < 1:
        raise ValueError("Quantity must be at least 1.")

    # --- 1. Lock the variant row (prevents concurrent available-stock races) ---
    locked_variant = (
        ProductVariant.objects
        .select_for_update()
        .get(pk=variant.pk)
    )

    # --- 2. Compute available stock ---
    active_reserved = (
        Reservation.objects
        .filter(variant=locked_variant, status=ReservationStatus.ACTIVE)
        .aggregate(total=Sum("quantity"))["total"]
    ) or 0

    available = locked_variant.stock - active_reserved

    # --- 4. Duplicate active reservation guard ---
    if Reservation.objects.filter(
        user=user,
        variant=locked_variant,
        status=ReservationStatus.ACTIVE,
    ).exists():
        raise DuplicateActiveReservationError(
            "You already have an active reservation for this variant. "
            "Cancel or convert it before creating a new one."
        )

    # --- 5. Distinct-product limit ---
    active_product_count = (
        Reservation.objects
        .filter(user=user, status=ReservationStatus.ACTIVE)
        .values("variant__product_id")
        .distinct()
        .count()
    )
    # This product might already be in the set; only count it as new if not
    current_product_ids = set(
        Reservation.objects
        .filter(user=user, status=ReservationStatus.ACTIVE)
        .values_list("variant__product_id", flat=True)
    )
    if (
        locked_variant.product_id not in current_product_ids
        and active_product_count >= _MAX_DISTINCT_PRODUCTS_PER_USER
    ):
        raise ProductLimitExceededError(
            f"You can have at most {_MAX_DISTINCT_PRODUCTS_PER_USER} distinct "
            "products in active reservations."
        )

    # --- 6. Stock check ---
    if available < quantity:
        raise InsufficientStockError(
            f"Only {available} units available for this variant "
            f"(requested {quantity})."
        )

    # --- 7. Create reservation ---
    now = timezone.now()
    expires_at = now + timezone.timedelta(minutes=_TIMEOUT_MINUTES)

    reservation = Reservation.objects.create(
        user=user,
        variant=locked_variant,
        quantity=quantity,
        status=ReservationStatus.ACTIVE,
        expires_at=expires_at,
    )
    return reservation



# ---------------------------------------------------------------------------
# Public service: cancel reservation
# ---------------------------------------------------------------------------

@transaction.atomic
def cancel_reservation(reservation: Reservation) -> Reservation:
    """
    Cancel an ACTIVE reservation.  Stock is logically released immediately
    (no physical stock change needed since physical stock was never decremented).

    Raises:
        ReservationNotActiveError: reservation is not ACTIVE.
    """
    reservation = (
        Reservation.objects
        .select_for_update()
        .get(pk=reservation.pk)
    )

    if reservation.status != ReservationStatus.ACTIVE:
        raise ReservationNotActiveError(
            f"Only ACTIVE reservations can be cancelled. "
            f"Current status: {reservation.status!r}."
        )

    reservation.status = ReservationStatus.CANCELLED
    reservation.save(update_fields=["status", "updated_at"])
    return reservation


# ---------------------------------------------------------------------------
# Public service: checkout — convert reservations → Order
# ---------------------------------------------------------------------------

@transaction.atomic
def checkout_from_reservations(
    user: User,
    reservation_ids: list,
    delivery_address: DeliveryAddress,
    delivery_fee: Decimal = Decimal("0.00"),
) -> Order:
    """
    Atomically convert a list of ACTIVE reservations into a confirmed Order.

    Steps:
        1. Load & sort reservations (lock-ordering by variant UUID).
        2. Validate delivery_address belongs to user.
        3. Lock all referenced variants in UUID order (deadlock-safe).
        4. For each reservation: validate status=ACTIVE & not expired.
        5. Validate all product currencies are uniform.
        6. Snapshot prices, build OrderItem objects.
        7. Decrement physical stock via F() expression.
        8. Mark reservations as CONVERTED.
        9. Create Order(status=RESERVED) + bulk-create OrderItems.

    Raises:
        ReservationConversionError: any reservation is expired, already
            converted, or stock is somehow below zero.
        ValueError: delivery_address does not belong to user.
        ValueError: mixed currencies across products.
    """
    # Lock reservations in PK order (consistent ordering prevents deadlock).
    # select_for_update() ensures concurrent checkout requests serialize here:
    # the second request blocks until the first has committed and its
    # reservations are already CONVERTED, so the second will find 0 rows and
    # raise ReservationConversionError cleanly.
    reservations = list(
        Reservation.objects
        .select_related("variant__product")
        .select_for_update()                          # BUG-13 fix: lock rows
        .filter(pk__in=reservation_ids, user=user, status=ReservationStatus.ACTIVE)
        .order_by("id")   # Lock in PK order to prevent deadlock
    )

    if len(reservations) != len(reservation_ids):
        found_ids = {str(r.pk) for r in reservations}
        missing = [str(rid) for rid in reservation_ids if str(rid) not in found_ids]
        raise ReservationConversionError(
            f"Reservations not found or not ACTIVE: {missing}. "
            "They may have expired or already been converted."
        )

    # --- 2. Validate delivery address ownership ---
    if delivery_address.user_id != user.pk:
        raise ValueError("Delivery address does not belong to this user.")

    # --- 3. Lock variants in UUID order (deadlock-safe) ---
    variant_ids = sorted({str(r.variant_id) for r in reservations})
    locked_variants = {
        str(v.pk): v
        for v in ProductVariant.objects.select_for_update().filter(
            id__in=variant_ids
        )
    }

    # --- 4. Re-validate each reservation AFTER holding both the reservation
    #         lock and the variant lock (this is the true race-free checkpoint)
    now = timezone.now()
    for reservation in reservations:
        # Re-check status: another transaction may have converted/cancelled
        # this reservation between our query and now.
        if reservation.status != ReservationStatus.ACTIVE:
            raise ReservationConversionError(
                f"Reservation {reservation.pk} is no longer ACTIVE "
                f"(status={reservation.status!r}). It may have just been converted "
                "by a concurrent checkout."
            )
        if reservation.expires_at < now:
            raise ReservationConversionError(
                f"Reservation {reservation.pk} for variant "
                f"{reservation.variant.sku!r} has expired."
            )

    # --- 5. Validate currency uniformity ---
    currencies = {r.variant.product.currency for r in reservations}
    if len(currencies) != 1:
        raise ValueError(
            "All items in a single order must share the same currency."
        )
    order_currency = currencies.pop()

    # --- 6. Build items, snapshot prices ---
    subtotal = Decimal("0.00")
    item_objects: list[OrderItem] = []
    price_snapshots: dict[str, Decimal] = {}

    for reservation in reservations:
        variant = locked_variants[str(reservation.variant_id)]
        price = variant.effective_price
        line_total = (price * reservation.quantity).quantize(Decimal("0.01"))
        subtotal += line_total
        price_snapshots[str(reservation.pk)] = price

    # --- 7. Create Order header ---
    order = Order.objects.create(
        user=user,
        status=OrderStatus.CREATED,
        currency=order_currency,
        delivery_address=delivery_address,
        delivery_fee=delivery_fee,
        total_amount=Decimal("0.00"),   # updated below
    )

    # --- 8. Decrement stock + build OrderItem instances ---
    for reservation in reservations:
        variant = locked_variants[str(reservation.variant_id)]
        price = price_snapshots[str(reservation.pk)]
        line_total = (price * reservation.quantity).quantize(Decimal("0.01"))
        sku_label = f" ({variant.sku})"

        # Atomic stock decrement via F() — no read-modify-write race
        ProductVariant.objects.filter(pk=variant.pk).update(
            stock=F("stock") - reservation.quantity
        )

        item_objects.append(
            OrderItem(
                order=order,
                product=reservation.variant.product,
                variant=variant,
                reservation=reservation,
                product_name_snapshot=reservation.variant.product.name + sku_label,
                product_price_snapshot=price,
                quantity=reservation.quantity,
                line_total=line_total,
            )
        )

    OrderItem.objects.bulk_create(item_objects)

    # --- 9. Update order totals ---
    total_amount = subtotal.quantize(Decimal("0.01"))
    order.total_amount = total_amount
    order.status = OrderStatus.RESERVED
    order.save(update_fields=["total_amount", "status", "updated_at"])

    # --- 10. Mark reservations CONVERTED ---
    # Note: updated_at is omitted here — the model field has auto_now=True so
    # Django's ORM sets it to NOW() in the generated SQL automatically.
    Reservation.objects.filter(
        pk__in=[r.pk for r in reservations]
    ).update(status=ReservationStatus.CONVERTED)

    return order


# ---------------------------------------------------------------------------
# Public service: expire stale (called by Celery task — idempotent)
# ---------------------------------------------------------------------------

def expire_stale_reservations() -> int:
    """
    Bulk-expire all ACTIVE reservations whose expires_at is in the past.

    This is intentionally NOT wrapped in transaction.atomic — the UPDATE
    statement is atomic at the DB level.  Using select_for_update here would
    create page-level locks and dramatically slow the cleanup job.

    Returns the number of reservations expired.
    """
    now = timezone.now()
    # .update() returns a plain int (rows affected); tuple-unpacking raises ValueError.
    count = Reservation.objects.filter(
        status=ReservationStatus.ACTIVE,
        expires_at__lte=now,
    ).update(status=ReservationStatus.EXPIRED)
    return count
