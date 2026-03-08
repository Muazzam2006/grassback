from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import Withdrawal, WithdrawalStatus
from .permissions import IsAdminOnly, IsWithdrawalOwnerOrAdmin
from .serializers import (
    WithdrawalCreateSerializer,
    WithdrawalDetailSerializer,
    WithdrawalListSerializer,
    WithdrawalRejectSerializer,
)
from .services import (
    InvalidWithdrawalStateError,
    InsufficientBalanceError,
    approve_withdrawal,
    reject_withdrawal,
    request_withdrawal,
)


class WithdrawalViewSet(
    mixins.CreateModelMixin,
    mixins.RetrieveModelMixin,
    mixins.ListModelMixin,
    viewsets.GenericViewSet,
):
    

    lookup_field = "id"
    http_method_names = ["get", "post", "head", "options"]

    def get_permissions(self):
        if self.action in ("approve", "reject"):
            return [IsAuthenticated(), IsAdminOnly()]
        return [IsAuthenticated(), IsWithdrawalOwnerOrAdmin()]

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return Withdrawal.objects.none()

        user = self.request.user
        qs = Withdrawal.objects.select_related("user", "processed_by")

        if not user.is_authenticated:
            return qs.none()

        if user.is_staff:
            return qs
        return qs.filter(user=user)

    def get_serializer_class(self):
        if self.action == "create":
            return WithdrawalCreateSerializer
        if self.action == "retrieve":
            return WithdrawalDetailSerializer
        return WithdrawalListSerializer

    def create(self, request, *args, **kwargs):
        serializer = WithdrawalCreateSerializer(
            data=request.data,
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)
        amount = serializer.validated_data["amount"]
        try:
            withdrawal = request_withdrawal(
                user=request.user,
                amount=amount,
                currency="USD",
            )
        except InsufficientBalanceError as exc:
            return Response(
                {"detail": str(exc)},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(
            WithdrawalDetailSerializer(withdrawal).data,
            status=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=["post"], url_path="approve")
    def approve(self, request, id=None):
        withdrawal = self.get_object()
        try:
            withdrawal = approve_withdrawal(withdrawal, admin_user=request.user)
        except InvalidWithdrawalStateError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_409_CONFLICT)
        return Response(WithdrawalDetailSerializer(withdrawal).data)

    @action(detail=True, methods=["post"], url_path="reject")
    def reject(self, request, id=None):
        withdrawal = self.get_object()
        serializer = WithdrawalRejectSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            withdrawal = reject_withdrawal(
                withdrawal,
                admin_user=request.user,
                reason=serializer.validated_data["reason"],
            )
        except InvalidWithdrawalStateError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_409_CONFLICT)
        return Response(WithdrawalDetailSerializer(withdrawal).data)
