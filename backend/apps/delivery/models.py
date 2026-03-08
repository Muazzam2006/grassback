
import uuid

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models
from django.utils.translation import gettext_lazy as _
from decimal import Decimal


class DeliveryStatus(models.TextChoices):
    PENDING = "PENDING", _("Pending")
    SHIPPED = "SHIPPED", _("Shipped")
    DELIVERED = "DELIVERED", _("Delivered")
    CANCELLED = "CANCELLED", _("Cancelled")


class DeliveryAddress(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="delivery_addresses",
    )
    first_name = models.CharField(max_length=100, verbose_name=_("First Name"))
    last_name = models.CharField(max_length=100, verbose_name=_("Last Name"))
    phone = models.CharField(max_length=20, verbose_name=_("Phone"))
    region = models.CharField(max_length=100, verbose_name=_("Region / Oblast"))
    city = models.CharField(max_length=100, verbose_name=_("City"))
    street = models.CharField(max_length=255, verbose_name=_("Street Address"))
    apartment = models.CharField(max_length=50, blank=True, verbose_name=_("Apartment / Unit"))
    postal_code = models.CharField(max_length=20, blank=True, verbose_name=_("Postal Code"))
    is_default = models.BooleanField(default=False, db_index=True, verbose_name=_("Default Address"))
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "delivery_address"
        verbose_name = _("Delivery Address")
        verbose_name_plural = _("Delivery Addresses")
        ordering = ["-is_default", "-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["user"],
                condition=models.Q(is_default=True),
                name="one_default_address_per_user",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.first_name} {self.last_name} — {self.city}, {self.street}"


class Courier(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    phone = models.CharField(max_length=20, unique=True, db_index=True)
    is_active = models.BooleanField(default=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "delivery_courier"
        verbose_name = _("Courier")
        verbose_name_plural = _("Couriers")
        ordering = ["last_name", "first_name"]

    def __str__(self) -> str:
        return f"{self.first_name} {self.last_name} ({self.phone})"


class OrderDelivery(models.Model):

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order = models.OneToOneField(
        "orders.Order",
        on_delete=models.PROTECT,
        related_name="delivery",
    )
    delivery_address = models.ForeignKey(
        DeliveryAddress,
        on_delete=models.PROTECT,
        related_name="deliveries",
        verbose_name=_("Delivery Address"),
    )
    courier = models.ForeignKey(
        Courier,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="deliveries",
        verbose_name=_("Assigned Courier"),
    )
    status = models.CharField(
        max_length=10,
        choices=DeliveryStatus.choices,
        default=DeliveryStatus.PENDING,
        db_index=True,
    )
    tracking_number = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        unique=True,
        verbose_name=_("Tracking Number"),
    )
    delivery_fee = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0.00"))],
        verbose_name=_("Delivery Fee"),
    )
    notes = models.TextField(blank=True, verbose_name=_("Delivery Notes"))
    estimated_delivery_at = models.DateTimeField(null=True, blank=True)
    shipped_at = models.DateTimeField(null=True, blank=True)
    delivered_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "delivery_order_delivery"
        verbose_name = _("Order Delivery")
        verbose_name_plural = _("Order Deliveries")
        ordering = ["-created_at"]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(delivery_fee__gte=0),
                name="order_delivery_fee_gte_0",
            ),
        ]
        indexes = [
            models.Index(fields=["status"], name="order_delivery_status_idx"),
            models.Index(fields=["courier", "status"], name="ord_dlv_courier_status_idx"),
        ]

    def __str__(self) -> str:
        return f"OrderDelivery(order={self.order_id}, status={self.status})"
