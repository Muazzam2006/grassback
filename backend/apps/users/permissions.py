from rest_framework import permissions


class IsSelfOrAdmin(permissions.BasePermission):

    def has_permission(self, request, view) -> bool:
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.is_active
        )

    def has_object_permission(self, request, view, obj) -> bool:
        return request.user.is_staff or obj.pk == request.user.pk


class IsAdminOnly(permissions.BasePermission):

    def has_permission(self, request, view) -> bool:
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.is_active
            and request.user.is_staff
        )
