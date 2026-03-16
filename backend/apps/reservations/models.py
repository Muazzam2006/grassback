import uuid

from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _


class ReservationStatus(models.TextChoices):
    ACTIVE = "ACTIVE", _("Active")
    EXPIRED = "EXPIRED", _("Expired")
    CONVERTED = "CONVERTED", _("Converted")
    CANCELLED = "CANCELLED", _("Cancelled")


class Reservation(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="reservations",
        verbose_name=_("User"),
    )
    variant = models.ForeignKey(
        "products.ProductVariant",
        on_delete=models.CASCADE,
        related_name="reservations",
        verbose_name=_("Product Variant"),
    )
    quantity = models.PositiveSmallIntegerField(
        verbose_name=_("Quantity"),
        help_text=_("Units reserved (must be >= 1)."),
    )
    status = models.CharField(
        max_length=12,
        choices=ReservationStatus.choices,
        default=ReservationStatus.ACTIVE,
        db_index=True,
        verbose_name=_("Status"),
    )
    expires_at = models.DateTimeField(
        verbose_name=_("Expires At"),
        help_text=_("UTC timestamp when this reservation expires if not converted."),
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "reservations_reservation"
        verbose_name = _("Reservation")
        verbose_name_plural = _("Reservations")
        ordering = ["-created_at"]

        constraints = [
            models.CheckConstraint(
                condition=models.Q(quantity__gte=1),
                name="resv_qty_gte_1",
            ),
        ]
        indexes = [
                                                                                             
            models.Index(
                fields=["expires_at"],
                condition=models.Q(status=ReservationStatus.ACTIVE),
                name="resv_active_expires_idx",
            ),
                                                
            models.Index(
                fields=["user", "status"],
                name="reservation_user_status_idx",
            ),
                                                         
            models.Index(
                fields=["variant", "status"],
                name="reservation_variant_status_idx",
            ),
        ]

    def __str__(self) -> str:
        status_map = {
            ReservationStatus.ACTIVE: "Активен",
            ReservationStatus.EXPIRED: "Истек",
            ReservationStatus.CONVERTED: "Преобразован в заказ",
            ReservationStatus.CANCELLED: "Отменен",
        }
        status_label = status_map.get(self.status, self.status)
        user_phone = getattr(self.user, "phone", self.user_id)
        variant_sku = getattr(self.variant, "sku", self.variant_id)
        return (
            f"Резерв {str(self.id)[:8]} "
            f"(пользователь: {user_phone}, "
            f"вариант: {variant_sku}, "
            f"кол-во: {self.quantity}, "
            f"статус: {status_label})"
        )

    @property
    def is_active(self) -> bool:
        return self.status == ReservationStatus.ACTIVE
