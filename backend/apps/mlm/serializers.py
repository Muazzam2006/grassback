from rest_framework import serializers

from .models import StatusThreshold


class StatusThresholdSerializer(serializers.ModelSerializer):
    """
    Read-only serializer for status promotion thresholds.
    Agents can view thresholds to understand what's required for promotion.
    """

    class Meta:
        model = StatusThreshold
        fields = [
            "status",
            "min_personal_turnover",
            "min_team_turnover",
        ]
        read_only_fields = fields
