from decimal import Decimal

from rest_framework import serializers

from .models import Order, OrderItem, OrderLifecycleLog, OrderStatus

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


class OrderListSerializer(serializers.ModelSerializer):
    order_number = serializers.CharField(read_only=True)
    grand_total = serializers.DecimalField(
        max_digits=14, decimal_places=2, read_only=True
    )

    class Meta:
        model = Order
        fields = [
            "id", "order_number", "status",
            "total_amount", "delivery_fee", "grand_total",
            "currency", "delivery_address", "created_at",
        ]
        read_only_fields = fields


class OrderDetailSerializer(serializers.ModelSerializer):
    order_number = serializers.CharField(read_only=True)
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
            "id", "order_number", "user", "status",
            "items",
            "total_amount", "delivery_fee", "grand_total",
            "currency", "delivery_address",
            "lifecycle",
            "created_at", "updated_at",
        ]
        read_only_fields = fields


class OrderStatusTransitionSerializer(serializers.Serializer):
    note = serializers.CharField(
        max_length=500, required=False, default="", allow_blank=True
    )
    tracking_number = serializers.CharField(
        max_length=200, required=False, default="", allow_blank=True,
        help_text="Populated on SHIP transition.",
    )
