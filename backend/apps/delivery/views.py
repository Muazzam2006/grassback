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


class IsAddressOwnerOrAdmin(BasePermission):
    def has_object_permission(self, request, view, obj):
        return request.user.is_staff or obj.user_id == request.user.pk
                                                                          

class DeliveryAddressViewSet(viewsets.ModelViewSet):
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
                                                                     
        return DeliveryAddress.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class CourierViewSet(viewsets.ModelViewSet):
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
