"""
Order views — COD lifecycle (v3).

Orders are READ-only from the user perspective.
Creation via POST /api/v1/reservations/checkout/.

Admins can advance the lifecycle via custom actions:
  POST /api/v1/orders/{id}/confirm/
  POST /api/v1/orders/{id}/ship/
  POST /api/v1/orders/{id}/deliver/
  POST /api/v1/orders/{id}/cancel/
"""
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.users.permissions import IsAdminOnly

from .models import Order, OrderStatus
from .serializers import (
    OrderDetailSerializer,
    OrderListSerializer,
    OrderStatusTransitionSerializer,
)
from .services import (
    OrderTransitionError,
    cancel_order,
    confirm_order,
    deliver_order,
    ship_order,
)


class OrderViewSet(
    mixins.RetrieveModelMixin,
    mixins.ListModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet,
):
    """
    Users: read + destroy (pre-DELIVERED only).
    Admins: also access lifecycle transitions.
    """
    permission_classes = [IsAuthenticated]
    lookup_field = "id"
    # Enables ?status=CREATED / ?status=CANCELLED / etc.
    # Uses the globally-configured DjangoFilterBackend — no extra setup needed.
    filterset_fields = ["status"]

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return Order.objects.none()

        qs = Order.objects.select_related(
            "user", "delivery_address"
        ).prefetch_related(
            "items__product", "items__variant", "lifecycle_logs"
        )

        if not self.request.user.is_authenticated:
            return qs.none()

        if self.request.user.is_staff:
            return qs
        return qs.filter(user=self.request.user)

    def get_serializer_class(self):
        if self.action == "retrieve":
            return OrderDetailSerializer
        return OrderListSerializer

    def destroy(self, request, *args, **kwargs):
        """
        Soft-cancel an order (no hard DELETE from the database).

        Using cancel_order instead of instance.delete() ensures that physical
        stock is restored atomically for any RESERVED/CONFIRMED/SHIPPED order
        and an audit log entry is written.

        Returns 409 Conflict — not 403 — when the order is already terminal
        (DELIVERED or CANCELLED), because the problem is resource state, not
        permissions.
        """
        order = self.get_object()
        try:
            cancel_order(
                order,
                changed_by=request.user,
                note="Cancelled by user via API.",
            )
        except OrderTransitionError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_409_CONFLICT)
        return Response(status=status.HTTP_204_NO_CONTENT)

    # ------------------------------------------------------------------ #
    # Admin lifecycle transitions                                          #
    # ------------------------------------------------------------------ #

    def _lifecycle_action(self, request, service_fn, **service_kwargs):
        """Shared helper for all lifecycle transition endpoints."""
        order = self.get_object()
        note_serializer = OrderStatusTransitionSerializer(data=request.data)
        note_serializer.is_valid(raise_exception=True)
        note = note_serializer.validated_data.get("note", "")

        try:
            order = service_fn(order, admin_user=request.user, note=note, **service_kwargs)
        except OrderTransitionError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_409_CONFLICT)
        return Response(OrderDetailSerializer(order).data)

    @action(detail=True, methods=["post"], url_path="confirm",
            permission_classes=[IsAuthenticated, IsAdminOnly])
    def confirm(self, request, id=None):
        """POST /orders/{id}/confirm/ — RESERVED → CONFIRMED."""
        return self._lifecycle_action(request, confirm_order)

    @action(detail=True, methods=["post"], url_path="ship",
            permission_classes=[IsAuthenticated, IsAdminOnly])
    def ship(self, request, id=None):
        """POST /orders/{id}/ship/ — CONFIRMED → SHIPPED."""
        note_s = OrderStatusTransitionSerializer(data=request.data)
        note_s.is_valid(raise_exception=True)
        order = self.get_object()
        try:
            order = ship_order(
                order,
                admin_user=request.user,
                tracking_number=note_s.validated_data.get("tracking_number", ""),
                note=note_s.validated_data.get("note", ""),
            )
        except OrderTransitionError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_409_CONFLICT)
        return Response(OrderDetailSerializer(order).data)

    @action(detail=True, methods=["post"], url_path="deliver",
            permission_classes=[IsAuthenticated, IsAdminOnly])
    def deliver(self, request, id=None):
        """
        POST /orders/{id}/deliver/ — SHIPPED → DELIVERED.
        Bonus pipeline is dispatched by Order post_save signal.
        """
        order = self.get_object()
        note_s = OrderStatusTransitionSerializer(data=request.data)
        note_s.is_valid(raise_exception=True)

        try:
            order = deliver_order(
                order,
                admin_user=request.user,
                note=note_s.validated_data.get("note", ""),
            )
        except OrderTransitionError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_409_CONFLICT)

        return Response(OrderDetailSerializer(order).data)

    @action(detail=True, methods=["post"], url_path="cancel")
    def cancel(self, request, id=None):
        """
        POST /orders/{id}/cancel/ — any pre-DELIVERED → CANCELLED.
        Users can cancel their own orders; admins can cancel any.
        """
        order = self.get_object()
        if not request.user.is_staff and order.user_id != request.user.pk:
            raise PermissionDenied("You cannot cancel this order.")

        note_s = OrderStatusTransitionSerializer(data=request.data)
        note_s.is_valid(raise_exception=True)

        try:
            order = cancel_order(
                order,
                changed_by=request.user,
                note=note_s.validated_data.get("note", "Cancelled by user."),
            )
        except OrderTransitionError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_409_CONFLICT)
        return Response(OrderDetailSerializer(order).data)
