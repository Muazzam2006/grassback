"""
Order models — COD lifecycle (v3).

OrderStatus changes (v3)
------------------------
Old:  PENDING → PAID → CANCELLED
New:  CREATED → RESERVED → CONFIRMED → SHIPPED → DELIVERED → CANCELLED

Financial semantics
-------------------
- COD: there is no PAID status.  Financial validity = DELIVERED.
- Bonuses trigger ONLY at DELIVERED (see bonuses/services.py).
- stock is decremented when status transitions CREATED → RESERVED
  (inside checkout_from_reservations service).

delivery_address is mandatory (NOT NULL, PROTECT).
delivery_fee is snapshotted at checkout from the user-provided value.
grand_total = total_amount + delivery_fee (read-only property).
"""
import uuid
from decimal import Decimal

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models
from django.utils.translation import gettext_lazy as _


class OrderStatus(models.TextChoices):
    CREATED = "CREATED", _("Created")           # Order header exists, stock reserved
    RESERVED = "RESERVED", _("Reserved")         # Reservations converted, stock decremented
    CONFIRMED = "CONFIRMED", _("Confirmed")       # Admin confirmed, ready to pack
    SHIPPED = "SHIPPED", _("Shipped")             # Handed to courier
    DELIVERED = "DELIVERED", _("Delivered")       # COD received — bonuses trigger here
    CANCELLED = "CANCELLED", _("Cancelled")       # Cancelled at any pre-DELIVERED stage


class Order(models.Model):
    """
    Order header.

    v3 additions:
        delivery_address — mandatory FK to DeliveryAddress; PROTECT prevents
                           deletion of an address that has active orders.
        status           — 6-value COD lifecycle (replaces PENDING/PAID).
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="orders",
    )
    status = models.CharField(
        max_length=12,
        choices=OrderStatus.choices,
        default=OrderStatus.CREATED,
        db_index=True,
    )
    delivery_address = models.ForeignKey(
        "delivery.DeliveryAddress",
        on_delete=models.PROTECT,
        related_name="orders",
        verbose_name=_("Delivery Address"),
        help_text=_("Mandatory — where COD goods will be delivered."),
    )
    total_amount = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=Decimal("0.00"),
        help_text=_("Items subtotal (quantity × effective price for each line)."),
    )
    delivery_fee = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=Decimal("0.00"),
        help_text=_("Snapshot of delivery fee at time of checkout."),
    )
    currency = models.CharField(max_length=3, default="USD")
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "orders_order"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user", "status"], name="order_user_status_idx"),
        ]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(total_amount__gte=0),
                name="orders_order_total_amount_gte_0",
            ),
            models.CheckConstraint(
                condition=models.Q(delivery_fee__gte=0),
                name="orders_order_delivery_fee_gte_0",
            ),
        ]

    @property
    def grand_total(self) -> Decimal:
        """Payment total: items subtotal + delivery fee."""
        return self.total_amount + self.delivery_fee

    def __str__(self):
        return f"Order({self.id}, user={self.user_id}, {self.status})"


class OrderItem(models.Model):
    """
    Immutable line item snapshotting price at time of checkout.

    v3 addition:
        reservation — nullable FK audit trail linking the reservation that
                      produced this item (SET_NULL so items survive reservation cleanup).
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey(
        "products.Product",
        on_delete=models.PROTECT,
        related_name="order_items",
    )
    variant = models.ForeignKey(
        "products.ProductVariant",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="order_items",
        verbose_name=_("Product Variant (SKU)"),
    )
    reservation = models.ForeignKey(
        "reservations.Reservation",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="order_items",
        verbose_name=_("Source Reservation"),
        help_text=_("Audit trail: the reservation that was converted into this item."),
    )
    product_name_snapshot = models.CharField(
        max_length=255,
        help_text=_("Snapshot of product name at time of checkout."),
    )
    product_price_snapshot = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.00"))],
        help_text=_("Snapshot of effective price at time of checkout."),
    )
    quantity = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    line_total = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        help_text=_("quantity × product_price_snapshot — snapshotted at checkout."),
    )

    class Meta:
        db_table = "orders_order_item"
        constraints = [
            models.CheckConstraint(
                condition=models.Q(quantity__gt=0),
                name="order_item_quantity_gt_0",
            ),
            models.CheckConstraint(
                condition=models.Q(product_price_snapshot__gte=0),
                name="order_item_price_gte_0",
            ),
            models.CheckConstraint(
                condition=models.Q(line_total__gte=0),
                name="order_item_line_total_gte_0",
            ),
            models.UniqueConstraint(
                fields=["order", "product", "variant"],
                name="unique_product_variant_per_order",
            ),
        ]
        indexes = [
            models.Index(fields=["order"], name="order_item_order_idx"),
        ]

    def __str__(self):
        sku = f" SKU={self.variant.sku}" if self.variant_id else ""
        return f"{self.quantity}× {self.product_name_snapshot}{sku} in {self.order_id}"


class OrderLifecycleLog(models.Model):
    """
    Immutable audit trail of every order status transition.
    Written by order lifecycle service functions.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name="lifecycle_logs",
    )
    from_status = models.CharField(
        max_length=12,
        choices=OrderStatus.choices,
        blank=True,
        default="",
    )
    to_status = models.CharField(
        max_length=12,
        choices=OrderStatus.choices,
    )
    changed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="order_lifecycle_actions",
    )
    note = models.CharField(max_length=500, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        db_table = "orders_lifecycle_log"
        ordering = ["created_at"]
        indexes = [
            models.Index(fields=["order", "created_at"], name="order_log_order_ts_idx"),
        ]

    def __str__(self):
        return (
            f"Order {self.order_id}: {self.from_status or '—'} → {self.to_status} "
            f"at {self.created_at}"
        )