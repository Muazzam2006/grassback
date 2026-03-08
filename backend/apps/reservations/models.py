"""
Reservation model.

A Reservation logically fences stock for a product variant without touching
the physical ProductVariant.stock column.  Physical stock is only decremented
when a reservation is CONVERTED into an OrderItem at checkout.

Stock formula (computed via query — no cached counter):
  available = variant.stock − SUM(active_reservations.quantity)

Business rules enforced at service layer:
  • Quantity must be positive and cannot exceed current available stock.
  • Max 3 distinct products in ACTIVE reservations per user.
  • Reservation duration 15 days (RESERVATION_TIMEOUT_MINUTES, default 21600).

Concurrency:
  • Duplicate active (user, variant) prevented by partial unique index.
  • Race conditions on available-stock check prevented by select_for_update()
    on the ProductVariant row inside create_reservation().
"""
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
    """
    Time-limited soft reservation of a product variant for a user.
    """
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
            # For batch expiration job — covers WHERE status='ACTIVE' AND expires_at <= now()
            models.Index(
                fields=["expires_at"],
                condition=models.Q(status=ReservationStatus.ACTIVE),
                name="resv_active_expires_idx",
            ),
            # For user's active-reservation list
            models.Index(
                fields=["user", "status"],
                name="reservation_user_status_idx",
            ),
            # For available-stock computation per variant
            models.Index(
                fields=["variant", "status"],
                name="reservation_variant_status_idx",
            ),
        ]

    def __str__(self) -> str:
        return (
            f"Reservation({self.id!s:.8}, "
            f"user={self.user_id}, "
            f"variant={self.variant_id}, "
            f"qty={self.quantity}, "
            f"{self.status})"
        )

    @property
    def is_active(self) -> bool:
        return self.status == ReservationStatus.ACTIVE
