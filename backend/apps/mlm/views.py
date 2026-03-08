from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated

from .models import StatusThreshold
from .serializers import StatusThresholdSerializer


class StatusThresholdViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = StatusThreshold.objects.all().order_by("min_personal_turnover")
    serializer_class = StatusThresholdSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = None                                             
