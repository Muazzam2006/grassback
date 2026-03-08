from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters
from rest_framework.mixins import ListModelMixin, RetrieveModelMixin
from rest_framework.permissions import IsAuthenticated
from rest_framework.viewsets import GenericViewSet

from .filters import BonusFilter
from .models import Bonus
from .permissions import IsBonusOwnerOrAdmin
from .serializers import BonusDetailSerializer, BonusListSerializer


class BonusViewSet(ListModelMixin, RetrieveModelMixin, GenericViewSet):
    """
    Read-only viewset for Bonus records.

    - Authenticated users see only their own bonuses.
    - Staff see all bonuses.
    - No create / update / delete endpoints.
    """

    lookup_field = "id"
    permission_classes = [IsAuthenticated, IsBonusOwnerOrAdmin]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_class = BonusFilter
    ordering_fields = ["created_at", "level", "amount"]
    ordering = ["-created_at"]

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return Bonus.objects.none()

        qs = Bonus.objects.select_related("user", "source_user", "order")

        if not self.request.user.is_authenticated:
            return qs.none()

        if not self.request.user.is_staff:
            qs = qs.filter(user=self.request.user)

        return qs

    def get_serializer_class(self):
        if self.action == "retrieve":
            return BonusDetailSerializer
        return BonusListSerializer
