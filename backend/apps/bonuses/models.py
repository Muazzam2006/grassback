
import uuid
from decimal import Decimal

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models
from django.utils.translation import gettext_lazy as _



class BonusType(models.TextChoices):
    PERSONAL = "PERSONAL", _("Personal")
    TEAM = "TEAM", _("Team")


class BonusStatus(models.TextChoices):
    PENDING = "PENDING", _("Pending")
    CONFIRMED = "CONFIRMED", _("Confirmed")


class CalculationType(models.TextChoices):
    PERCENT = "PERCENT", _("Percentage")
    FIXED = "FIXED", _("Fixed Amount")


class MLMRule(models.Model):
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    agent_status = models.CharField(
        max_length=10,
        choices=[
            ("NEW", _("New")),
            ("BRONZE", _("Bronze")),
            ("SILVER", _("Silver")),
            ("GOLD", _("Gold")),
        ],
    )
    level = models.PositiveIntegerField(validators=[MinValueValidator(1)])

    calculation_type = models.CharField(
        max_length=10,
        choices=CalculationType.choices,
        default=CalculationType.PERCENT,
        verbose_name=_("Calculation Type"),
        help_text=_("PERCENT: value% of order total.  FIXED: flat amount per order."),
    )
    value = models.DecimalField(
        max_digits=12,
        decimal_places=4,
        validators=[MinValueValidator(Decimal("0.0000"))],
        verbose_name=_("Value"),
        help_text=_("Percentage (e.g. 5.25) or fixed amount depending on calculation_type."),
    )

    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "bonuses_mlm_rule"
        verbose_name = _("MLM Rule")
        verbose_name_plural = _("MLM Rules")
        ordering = ["agent_status", "level"]
        indexes = [
            models.Index(fields=["agent_status", "level"], name="mlm_rule_status_level_idx"),
            models.Index(fields=["is_active"], name="mlm_rule_is_active_idx"),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["agent_status", "level"],
                condition=models.Q(is_active=True),
                name="unique_active_mlm_rule_status_level",
            ),
            models.CheckConstraint(
                condition=models.Q(value__gte=0),
                name="mlm_rule_value_gte_0",
            ),
            models.CheckConstraint(
                condition=models.Q(level__gt=0),
                name="mlm_rule_level_gt_0",
            ),
        ]

    def __str__(self) -> str:
        unit = "%" if self.calculation_type == CalculationType.PERCENT else "flat"
        return f"MLMRule({self.agent_status}, L{self.level}, {self.value}{unit})"

    @property
    def percent(self) -> Decimal:
        """Alias for `value` when calculation_type == PERCENT (read-only)."""
        return self.value

    @percent.setter
    def percent(self, new_value: Decimal) -> None:
        """Backward-compat alias used by legacy code/tests."""
        self.value = new_value


class Bonus(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="bonuses_received",
    )
    source_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="bonuses_generated",
    )
    order = models.ForeignKey(
        "orders.Order",
        on_delete=models.PROTECT,
        related_name="bonuses",
    )
    level = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    bonus_type = models.CharField(
        max_length=10,
        choices=BonusType.choices,
        default=BonusType.PERSONAL,
    )

    percent_snapshot = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal("0.00"))],
        help_text=_("Deprecated in v2. Use applied_value_snapshot instead."),
    )

    calculation_type_snapshot = models.CharField(
        max_length=10,
        choices=CalculationType.choices,
        default=CalculationType.PERCENT,
        verbose_name=_("Calculation Type (Snapshot)"),
    )
    applied_value_snapshot = models.DecimalField(
        max_digits=12,
        decimal_places=4,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal("0.0000"))],
        verbose_name=_("Applied Value (Snapshot)"),
        help_text=_("The rule value (% or flat) that produced this bonus amount."),
    )

    amount = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.01"))],
    )
    status = models.CharField(
        max_length=10,
        choices=BonusStatus.choices,
        default=BonusStatus.PENDING,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "bonuses_bonus"
        verbose_name = _("Bonus")
        verbose_name_plural = _("Bonuses")
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user"], name="bonus_user_idx"),
            models.Index(fields=["order"], name="bonus_order_idx"),
            models.Index(fields=["status"], name="bonus_status_idx"),
            models.Index(fields=["created_at"], name="bonus_created_at_idx"),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["user", "order", "level", "bonus_type"],
                name="uniq_bonus_user_order_lvl_tp",
            ),
            models.CheckConstraint(
                condition=models.Q(amount__gt=0),
                name="bonus_amount_gt_0",
            ),
            models.CheckConstraint(
                condition=~models.Q(user=models.F("source_user")),
                name="bonus_user_not_source_user",
            ),
            models.CheckConstraint(
                condition=models.Q(level__gt=0),
                name="bonus_level_gt_0",
            ),
        ]

    def __str__(self) -> str:
        return f"Bonus({self.user_id}, order={self.order_id}, L{self.level}, {self.amount})"

    def save(self, *args, **kwargs):
        if not self._state.adding:
            raise ValueError("Bonus records are immutable and cannot be modified after creation.")
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValueError("Bonus records cannot be deleted.")
