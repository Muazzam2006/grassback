from decimal import Decimal

from rest_framework import serializers

from .models import Courier, DeliveryAddress, DeliveryStatus, OrderDelivery


class DeliveryAddressSerializer(serializers.ModelSerializer):
    class Meta:
        model = DeliveryAddress
        fields = [
            "id", "first_name", "last_name", "phone",
            "region", "city", "street", "apartment", "postal_code",
            "is_default", "created_at",
        ]
        read_only_fields = ["id", "created_at"]


class CourierSerializer(serializers.ModelSerializer):
    class Meta:
        model = Courier
        fields = ["id", "first_name", "last_name", "phone", "is_active"]
        read_only_fields = ["id"]


class OrderDeliveryListSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderDelivery
        fields = [
            "id", "order", "status", "delivery_fee",
            "tracking_number", "shipped_at", "delivered_at",
        ]
        read_only_fields = fields


class OrderDeliveryDetailSerializer(serializers.ModelSerializer):
    delivery_address = DeliveryAddressSerializer(read_only=True)
    courier = CourierSerializer(read_only=True)

    class Meta:
        model = OrderDelivery
        fields = [
            "id", "order", "delivery_address", "courier", "status",
            "tracking_number", "delivery_fee", "notes",
            "estimated_delivery_at", "shipped_at", "delivered_at",
            "created_at", "updated_at",
        ]
        read_only_fields = fields


class OrderDeliveryCreateSerializer(serializers.Serializer):
    """
    Input for creating a delivery task against an existing confirmed order.

    `delivery_address` is NOT required — it is always taken automatically from
    `Order.delivery_address` (the address the customer entered at checkout).

    `delivery_fee` is optional.  When omitted, the fee already snapshotted on
    the Order at checkout is reused.  Pass it explicitly when the actual
    shipping cost differs from the estimate.
    """
    order = serializers.UUIDField()
    delivery_fee = serializers.DecimalField(
        max_digits=14, decimal_places=2,
        min_value=Decimal("0.00"),
        required=False,
        allow_null=True,
        help_text="Leave blank to reuse the fee already set on the order.",
    )
    courier = serializers.UUIDField(required=False, allow_null=True)
    notes = serializers.CharField(max_length=1000, allow_blank=True, default="")


class DeliveryStatusUpdateSerializer(serializers.Serializer):
    """Input for transitioning delivery status."""
    status = serializers.ChoiceField(choices=DeliveryStatus.choices)
    tracking_number = serializers.CharField(max_length=100, required=False, allow_blank=True)
    courier = serializers.UUIDField(required=False, allow_null=True)
    notes = serializers.CharField(max_length=1000, required=False, allow_blank=True)
