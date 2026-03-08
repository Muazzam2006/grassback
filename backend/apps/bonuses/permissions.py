from rest_framework.permissions import BasePermission, SAFE_METHODS


class IsBonusOwnerOrAdmin(BasePermission):

    message = "You do not have permission to access this bonus."

    def has_permission(self, request, view) -> bool:
        return request.method in SAFE_METHODS

    def has_object_permission(self, request, view, obj) -> bool:
        return request.user.is_staff or obj.user_id == request.user.pk
