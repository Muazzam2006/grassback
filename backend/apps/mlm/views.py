from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated

from .models import StatusThreshold
from .serializers import StatusThresholdSerializer


class StatusThresholdViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Read-only endpoint: returns all configured status promotion thresholds.
    Authenticated agents can see what's required to advance to the next level.
    Admin CRUD is through Django Admin only — API is intentionally read-only.
    """

    queryset = StatusThreshold.objects.all().order_by("min_personal_turnover")
    serializer_class = StatusThresholdSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = None  # Only 3 rows maximum; no pagination needed
