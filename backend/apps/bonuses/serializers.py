from rest_framework import serializers

from .models import Bonus                                                               

class BonusListSerializer(serializers.ModelSerializer):

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


class BonusDetailSerializer(serializers.ModelSerializer):

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
