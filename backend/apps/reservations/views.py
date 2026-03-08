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
        from apps.delivery.models import DeliveryAddress
        from apps.orders.serializers import OrderDetailSerializer

        serializer = CheckoutSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        d = serializer.validated_data

                                  
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
