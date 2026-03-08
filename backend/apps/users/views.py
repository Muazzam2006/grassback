from django.contrib.auth import get_user_model
from rest_framework import status, viewsets
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from apps.users.permissions import IsAdminOnly, IsSelfOrAdmin
from apps.users.serializers import UserCreateSerializer, UserDetailSerializer, UserUpdateSerializer

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
        if self.action in ("update", "partial_update"):
            return UserUpdateSerializer
        return UserDetailSerializer

    def get_permissions(self):
        action_map = {
            "create": [AllowAny],
            "list": [IsAdminOnly],
            "destroy": [IsAdminOnly],
        }
        permission_classes = action_map.get(self.action, [IsSelfOrAdmin])
        return [p() for p in permission_classes]

    def destroy(self, request, *args, **kwargs):
        return Response(status=status.HTTP_405_METHOD_NOT_ALLOWED)
