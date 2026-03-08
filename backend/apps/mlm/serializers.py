from rest_framework import serializers

from .models import StatusThreshold


class StatusThresholdSerializer(serializers.ModelSerializer):

    class Meta:
        model = StatusThreshold
        fields = [
            "status",
            "min_personal_turnover",
            "min_team_turnover",
        ]
        read_only_fields = fields
