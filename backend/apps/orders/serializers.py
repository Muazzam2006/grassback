"""
Orders serializers — COD lifecycle (v3).

Read serializers expose the full lifecycle.
OrderCreateSerializer is removed — orders are now created via
POST /api/v1/reservations/checkout/ using CheckoutSerializer.
"""
from decimal import Decimal

from rest_framework import serializers

from .models import Order, OrderItem, OrderLifecycleLog, OrderStatus


# ---------------------------------------------------------------------------
# Sub-serializers
# ---------------------------------------------------------------------------

class OrderItemSerializer(serializers.ModelSerializer):
    variant_sku = serializers.CharField(source="variant.sku", read_only=True, default=None)

    class Meta:
        model = OrderItem
        fields = [
            "id",
            "product",
            "variant",
            "variant_sku",
            "product_name_snapshot",
            "product_price_snapshot",
            "quantity",
            "line_total",
            "reservation",
        ]
        read_only_fields = fields


class OrderLifecycleLogSerializer(serializers.ModelSerializer):
    changed_by = serializers.StringRelatedField()

    class Meta:
        model = OrderLifecycleLog
        fields = ["from_status", "to_status", "changed_by", "note", "created_at"]
        read_only_fields = fields


# ---------------------------------------------------------------------------
# Order read serializers
# ---------------------------------------------------------------------------

class OrderListSerializer(serializers.ModelSerializer):
    grand_total = serializers.DecimalField(
        max_digits=14, decimal_places=2, read_only=True
    )

    class Meta:
        model = Order
        fields = [
            "id", "status",
            "total_amount", "delivery_fee", "grand_total",
            "currency", "delivery_address", "created_at",
        ]
        read_only_fields = fields


class OrderDetailSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)
    user = serializers.StringRelatedField()
    grand_total = serializers.DecimalField(
        max_digits=14, decimal_places=2, read_only=True
    )
    lifecycle = OrderLifecycleLogSerializer(
        source="lifecycle_logs", many=True, read_only=True
    )

    class Meta:
        model = Order
        fields = [
            "id", "user", "status",
            "items",
            "total_amount", "delivery_fee", "grand_total",
            "currency", "delivery_address",
            "lifecycle",
            "created_at", "updated_at",
        ]
        read_only_fields = fields


# ---------------------------------------------------------------------------
# Admin-facing status transition serializer
# ---------------------------------------------------------------------------

class OrderStatusTransitionSerializer(serializers.Serializer):
    """Used by admin actions (ship, confirm, deliver, cancel)."""
    note = serializers.CharField(
        max_length=500, required=False, default="", allow_blank=True
    )
    tracking_number = serializers.CharField(
        max_length=200, required=False, default="", allow_blank=True,
        help_text="Populated on SHIP transition.",
    )