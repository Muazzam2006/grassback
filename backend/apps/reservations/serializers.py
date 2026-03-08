"""
Reservation serializers.
"""
from rest_framework import serializers

from .models import Reservation, ReservationStatus
from .services import (
    DuplicateActiveReservationError,
    InsufficientStockError,
    ProductLimitExceededError,
)


# ---------------------------------------------------------------------------
# Read serializers
# ---------------------------------------------------------------------------

class ReservationListSerializer(serializers.ModelSerializer):
    variant_sku = serializers.CharField(source="variant.sku", read_only=True)
    product_name = serializers.CharField(source="variant.product.name", read_only=True)

    class Meta:
        model = Reservation
        fields = [
            "id",
            "variant",
            "variant_sku",
            "product_name",
            "quantity",
            "status",
            "expires_at",
            "created_at",
        ]
        read_only_fields = fields


class ReservationDetailSerializer(serializers.ModelSerializer):
    variant_sku = serializers.CharField(source="variant.sku", read_only=True)
    product_name = serializers.CharField(source="variant.product.name", read_only=True)
    product_id = serializers.UUIDField(source="variant.product_id", read_only=True)
    is_expired = serializers.SerializerMethodField()

    class Meta:
        model = Reservation
        fields = [
            "id",
            "variant",
            "variant_sku",
            "product_id",
            "product_name",
            "quantity",
            "status",
            "expires_at",
            "is_expired",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields

    def get_is_expired(self, obj: Reservation) -> bool:
        from django.utils import timezone
        return obj.status == ReservationStatus.ACTIVE and obj.expires_at <= timezone.now()


# ---------------------------------------------------------------------------
# Write serializers
# ---------------------------------------------------------------------------

class ReservationCreateSerializer(serializers.Serializer):
    """Input: which variant + how many units to reserve."""
    variant_id = serializers.UUIDField()
    quantity = serializers.IntegerField(min_value=1)

    def validate_variant_id(self, value):
        from apps.products.models import ProductVariant
        try:
            variant = ProductVariant.objects.select_related("product").get(
                pk=value, is_active=True
            )
        except ProductVariant.DoesNotExist:
            raise serializers.ValidationError("Variant not found or inactive.")
        return variant

    def create_reservation(self, user):
        from .services import reserve_variant

        variant = self.validated_data["variant_id"]  # already resolved to instance
        quantity = self.validated_data["quantity"]

        try:
            return reserve_variant(user=user, variant=variant, quantity=quantity)
        except DuplicateActiveReservationError as exc:
            raise serializers.ValidationError({"variant_id": str(exc)})
        except ProductLimitExceededError as exc:
            raise serializers.ValidationError({"variant_id": str(exc)})
        except InsufficientStockError as exc:
            raise serializers.ValidationError({"quantity": str(exc)})


class CheckoutSerializer(serializers.Serializer):
    """Input for checkout: reservation IDs + delivery address + fee."""
    reservation_ids = serializers.ListField(
        child=serializers.UUIDField(),
        min_length=1,
        help_text="List of ACTIVE reservation UUIDs to convert into an order.",
    )
    delivery_address_id = serializers.UUIDField(
        help_text="UUID of the delivery address (must belong to the requesting user).",
    )
    delivery_fee = serializers.DecimalField(
        max_digits=10,
        decimal_places=2,
        min_value=0,
        default=0,
        help_text="Delivery fee to snapshot onto the order.",
    )

    def validate_reservation_ids(self, value):
        if len(value) != len(set(str(v) for v in value)):
            raise serializers.ValidationError("Duplicate reservation IDs are not allowed.")
        return value
