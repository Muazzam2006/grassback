from django.contrib.auth import get_user_model
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from apps.users.permissions import IsAdminOnly, IsSelfOrAdmin
from apps.users.serializers import (
    RegistrationOTPRequestSerializer,
    RegistrationOTPVerifySerializer,
    UserCreateSerializer,
    UserDetailSerializer,
    UserUpdateSerializer,
)
from apps.users.services import SmsConfigurationError, SmsDeliveryError

User = get_user_model()


class UserViewSet(viewsets.ModelViewSet):

    lookup_field = "pk"
    http_method_names = ["get", "post", "patch", "delete", "head", "options"]

    def get_queryset(self):
        user = self.request.user
        qs = User.objects.select_related("parent")

        if user.is_staff:
            return qs

        if user.is_authenticated:
            return qs.filter(pk=user.pk)

        return qs.none()

    def get_serializer_class(self):
        if self.action == "create":
            return UserCreateSerializer
        if self.action == "request_registration_otp":
            return RegistrationOTPRequestSerializer
        if self.action == "verify_registration_otp":
            return RegistrationOTPVerifySerializer
        if self.action in ("update", "partial_update"):
            return UserUpdateSerializer
        return UserDetailSerializer

    def get_permissions(self):
        action_map = {
            "create": [AllowAny],
            "request_registration_otp": [AllowAny],
            "verify_registration_otp": [AllowAny],
            "list": [IsAdminOnly],
            "destroy": [IsAdminOnly],
        }
        permission_classes = action_map.get(self.action, [IsSelfOrAdmin])
        return [p() for p in permission_classes]

    @action(detail=False, methods=["post"], url_path="request-registration-otp")
    def request_registration_otp(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            serializer.save()
        except SmsConfigurationError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        except SmsDeliveryError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_502_BAD_GATEWAY)

        return Response({"detail": "OTP code sent successfully."}, status=status.HTTP_200_OK)

    @action(detail=False, methods=["post"], url_path="verify-registration-otp")
    def verify_registration_otp(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({"detail": "OTP code verified successfully."}, status=status.HTTP_200_OK)

    def destroy(self, request, *args, **kwargs):
        return Response(status=status.HTTP_405_METHOD_NOT_ALLOWED)
