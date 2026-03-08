from rest_framework import serializers

from .models import Bonus


# ---------------------------------------------------------------------------
# Compact list representation — used in paginated listings
# ---------------------------------------------------------------------------

class BonusListSerializer(serializers.ModelSerializer):
    """Minimal fields optimised for list views with many rows."""

    class Meta:
        model = Bonus
        fields = [
            "id",
            "level",
            "bonus_type",
            "amount",
            "status",
            "created_at",
        ]
        read_only_fields = fields


# ---------------------------------------------------------------------------
# Full detail representation — used in single-object retrieve
# ---------------------------------------------------------------------------

class BonusDetailSerializer(serializers.ModelSerializer):
    """Full bonus record including related order and source agent identifiers.

    M-1: Previously identical to BonusListSerializer.  Differentiated here:
    the detail view adds `order`, `source_user`, and `percent_snapshot` which
    are expensive or verbose for bulk list responses.
    """

    source_user_phone = serializers.CharField(
        source="source_user.phone",
        read_only=True,
        allow_null=True,
    )
    order_id = serializers.UUIDField(source="order.id", read_only=True, allow_null=True)

    class Meta:
        model = Bonus
        fields = [
            "id",
            "order_id",
            "source_user",
            "source_user_phone",
            "level",
            "bonus_type",
            "calculation_type_snapshot",
            "applied_value_snapshot",
            "percent_snapshot",
            "amount",
            "status",
            "created_at",
        ]
        read_only_fields = fields
