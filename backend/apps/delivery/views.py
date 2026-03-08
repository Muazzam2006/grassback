"""
Delivery views.

Fixes applied
-------------
C-3: Replaced bare `except Exception` with specific `DoesNotExist` exceptions.
     Previously, programming errors (AttributeError, etc.) returned HTTP 400
     instead of propagating as 500, hiding real bugs.

C-4: Added `IsOwnerOrAdmin` object-level permission to `DeliveryAddressViewSet`.
     Previously a non-staff user could read/update/delete any other user's
     delivery address by guessing its UUID (horizontal privilege escalation).
"""
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import BasePermission, IsAuthenticated
from rest_framework.response import Response

from apps.users.permissions import IsAdminOnly

from .models import Courier, DeliveryAddress, OrderDelivery
from .serializers import (
    CourierSerializer,
    DeliveryAddressSerializer,
    DeliveryStatusUpdateSerializer,
    OrderDeliveryCreateSerializer,
    OrderDeliveryDetailSerializer,
    OrderDeliveryListSerializer,
)
from .services import (
    DeliveryError,
    assign_courier,
    create_order_delivery,
    update_delivery_status,
)


# ---------------------------------------------------------------------------
# Object-level permission: owner or admin (C-4)
# ---------------------------------------------------------------------------

class IsAddressOwnerOrAdmin(BasePermission):
    """Allow access only to the address owner or a staff user."""

    def has_object_permission(self, request, view, obj):
        return request.user.is_staff or obj.user_id == request.user.pk


# ---------------------------------------------------------------------------
# Views
# ---------------------------------------------------------------------------

class DeliveryAddressViewSet(viewsets.ModelViewSet):
    """CRUD for the authenticated user's own delivery addresses.

    C-4: Object-level permission enforced via IsAddressOwnerOrAdmin so that
    a non-staff user cannot access another user's address by UUID.
    """

    serializer_class = DeliveryAddressSerializer
    permission_classes = [IsAuthenticated, IsAddressOwnerOrAdmin]
    http_method_names = ["get", "post", "patch", "delete", "head", "options"]

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return DeliveryAddress.objects.none()

        if not self.request.user.is_authenticated:
            return DeliveryAddress.objects.none()

        if self.request.user.is_staff:
            return DeliveryAddress.objects.select_related("user").all()
        # Non-staff: always scope to own addresses — defence-in-depth
        return DeliveryAddress.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class CourierViewSet(viewsets.ModelViewSet):
    """Admin-only: CRUD for couriers."""
    queryset = Courier.objects.all()
    serializer_class = CourierSerializer
    permission_classes = [IsAuthenticated, IsAdminOnly]
    http_method_names = ["get", "post", "patch", "delete", "head", "options"]


class OrderDeliveryViewSet(
    mixins.CreateModelMixin,
    mixins.RetrieveModelMixin,
    mixins.ListModelMixin,
    viewsets.GenericViewSet,
):
    """
    Endpoints:
        POST    /deliveries/                     → create delivery (admin)
        GET     /deliveries/                     → list (admin=all, user=own)
        GET     /deliveries/{id}/               → detail
        POST    /deliveries/{id}/update_status/ → transition status (admin)
        POST    /deliveries/{id}/assign_courier/ → assign courier (admin)
    """

    lookup_field = "id"

    def get_permissions(self):
        if self.action in ("create", "update_status", "assign_courier_action"):
            return [IsAuthenticated(), IsAdminOnly()]
        return [IsAuthenticated()]

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return OrderDelivery.objects.none()

        qs = OrderDelivery.objects.select_related(
            "order", "delivery_address", "courier"
        )

        if not self.request.user.is_authenticated:
            return qs.none()

        if self.request.user.is_staff:
            return qs
        return qs.filter(order__user=self.request.user)

    def get_serializer_class(self):
        if self.action == "create":
            return OrderDeliveryCreateSerializer
        if self.action == "retrieve":
            return OrderDeliveryDetailSerializer
        return OrderDeliveryListSerializer

    def create(self, request, *args, **kwargs):
        from apps.orders.models import Order

        serializer = OrderDeliveryCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        d = serializer.validated_data

        try:
            order = Order.objects.get(pk=d["order"])
        except Order.DoesNotExist:
            return Response(
                {"order": "Order not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        courier = None
        if d.get("courier"):
            try:
                courier = Courier.objects.get(pk=d["courier"])
            except Courier.DoesNotExist:
                return Response(
                    {"courier": "Courier not found."},
                    status=status.HTTP_404_NOT_FOUND,
                )

        try:
            delivery = create_order_delivery(
                order=order,
                # delivery_address is taken from order.delivery_address inside the service
                delivery_fee=d.get("delivery_fee"),
                courier=courier,
                notes=d.get("notes", ""),
            )
        except DeliveryError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_409_CONFLICT)

        return Response(
            OrderDeliveryDetailSerializer(delivery).data,
            status=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=["post"], url_path="update_status")
    def update_status(self, request, id=None):
        delivery = self.get_object()
        serializer = DeliveryStatusUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        d = serializer.validated_data

        courier = None
        if d.get("courier"):
            try:
                courier = Courier.objects.get(pk=d["courier"])
            except Courier.DoesNotExist:
                return Response(
                    {"courier": "Courier not found."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        try:
            delivery = update_delivery_status(
                delivery,
                new_status=d["status"],
                courier=courier,
                tracking_number=d.get("tracking_number", ""),
                notes=d.get("notes", ""),
            )
        except DeliveryError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_409_CONFLICT)

        return Response(OrderDeliveryDetailSerializer(delivery).data)

    @action(detail=True, methods=["post"], url_path="assign_courier")
    def assign_courier_action(self, request, id=None):
        delivery = self.get_object()
        courier_id = request.data.get("courier")
        if not courier_id:
            return Response(
                {"courier": "This field is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            courier = Courier.objects.get(pk=courier_id)
        except Courier.DoesNotExist:
            return Response(
                {"courier": "Courier not found."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            delivery = assign_courier(delivery, courier)
        except DeliveryError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_409_CONFLICT)

        return Response(OrderDeliveryDetailSerializer(delivery).data)
