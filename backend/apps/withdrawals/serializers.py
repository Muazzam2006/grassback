from decimal import Decimal

from rest_framework import serializers

from .models import Withdrawal, WithdrawalStatus


class WithdrawalListSerializer(serializers.ModelSerializer):
    """Compact representation for list views."""

    class Meta:
        model = Withdrawal
        fields = [
            "id",
            "reference",
            "amount",
            "currency",
            "status",
            "requested_at",
        ]
        read_only_fields = fields


class WithdrawalDetailSerializer(serializers.ModelSerializer):
    """Full detail including processor info."""

    processed_by_phone = serializers.CharField(
        source="processed_by.phone",
        read_only=True,
        allow_null=True,
    )

    class Meta:
        model = Withdrawal
        fields = [
            "id",
            "reference",
            "amount",
            "currency",
            "status",
            "rejection_reason",
            "requested_at",
            "processed_at",
            "processed_by",
            "processed_by_phone",
        ]
        read_only_fields = fields


class WithdrawalCreateSerializer(serializers.Serializer):
    """Input for a new withdrawal request."""

    amount = serializers.DecimalField(
        max_digits=14,
        decimal_places=2,
        min_value=Decimal("0.01"),
    )

    def validate_amount(self, value: Decimal) -> Decimal:
        user = self.context["request"].user
        if user.bonus_balance < value:
            raise serializers.ValidationError(
                f"Insufficient balance. Available: {user.bonus_balance}."
            )
        return value


class WithdrawalRejectSerializer(serializers.Serializer):
    """Input for rejecting a withdrawal (admin action)."""

    reason = serializers.CharField(
        max_length=1000,
        allow_blank=True,
        default="",
    )
