"""
Reservation views.

Endpoints
---------
GET    /api/v1/reservations/                → list user's reservations
POST   /api/v1/reservations/                → create reservation
GET    /api/v1/reservations/{id}/           → detail
POST   /api/v1/reservations/{id}/cancel/    → cancel reservation
POST   /api/v1/reservations/checkout/       → convert reservations → Order
"""
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import Reservation, ReservationStatus
from .serializers import (
    CheckoutSerializer,
    ReservationCreateSerializer,
    ReservationDetailSerializer,
    ReservationListSerializer,
)
from .services import (
    ReservationConversionError,
    ReservationNotActiveError,
    cancel_reservation,
    checkout_from_reservations,
)


class ReservationViewSet(
    mixins.CreateModelMixin,
    mixins.RetrieveModelMixin,
    mixins.ListModelMixin,
    viewsets.GenericViewSet,
):
    """
    Reservations are user-scoped.  A user can only see and manage their own
    reservations.  Admin access via Django admin only.
    """
    permission_classes = [IsAuthenticated]
    lookup_field = "id"

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return Reservation.objects.none()

        if not self.request.user.is_authenticated:
            return Reservation.objects.none()

        return (
            Reservation.objects
            .select_related("variant__product")
            .filter(user=self.request.user, status=ReservationStatus.ACTIVE)
            .order_by("-created_at")
        )

    def get_serializer_class(self):
        if self.action == "retrieve":
            return ReservationDetailSerializer
        if self.action == "create":
            return ReservationCreateSerializer
        if self.action == "checkout":
            return CheckoutSerializer
        return ReservationListSerializer

    def create(self, request, *args, **kwargs):
        """POST /reservations/ — create a new soft reservation."""
        serializer = ReservationCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        reservation = serializer.create_reservation(user=request.user)
        return Response(
            ReservationDetailSerializer(reservation).data,
            status=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=["post"], url_path="cancel")
    def cancel(self, request, id=None):
        """POST /reservations/{id}/cancel/ — cancel ACTIVE reservation."""
        reservation = self.get_object()
        try:
            reservation = cancel_reservation(reservation)
        except ReservationNotActiveError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_409_CONFLICT)
        return Response(ReservationDetailSerializer(reservation).data)

    @action(detail=False, methods=["post"], url_path="checkout")
    def checkout(self, request, *args, **kwargs):
        """
        POST /reservations/checkout/

        Convert ACTIVE reservations into a RESERVED Order (COD).
        Requires:
          - reservation_ids: list of UUIDs
          - delivery_address_id: UUID
          - delivery_fee: decimal (optional, default 0)
        """
        from apps.delivery.models import DeliveryAddress
        from apps.orders.serializers import OrderDetailSerializer

        serializer = CheckoutSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        d = serializer.validated_data

        # Resolve delivery address
        try:
            address = DeliveryAddress.objects.get(pk=d["delivery_address_id"])
        except DeliveryAddress.DoesNotExist:
            return Response(
                {"delivery_address_id": "Delivery address not found."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if address.user_id != request.user.pk:
            return Response(
                {"delivery_address_id": "This address does not belong to you."},
                status=status.HTTP_403_FORBIDDEN,
            )

        try:
            order = checkout_from_reservations(
                user=request.user,
                reservation_ids=d["reservation_ids"],
                delivery_address=address,
                delivery_fee=d["delivery_fee"],
            )
        except ReservationConversionError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_409_CONFLICT)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(
            OrderDetailSerializer(order).data,
            status=status.HTTP_201_CREATED,
        )
