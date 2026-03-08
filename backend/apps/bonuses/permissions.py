from rest_framework.permissions import BasePermission, SAFE_METHODS


class IsBonusOwnerOrAdmin(BasePermission):
    """
    Read-only access: bonus recipient sees own records, staff sees all.
    Write access is unconditionally denied for all parties.

    Relies on IsAuthenticated being applied first in the ViewSet.
    """

    message = "You do not have permission to access this bonus."

    def has_permission(self, request, view) -> bool:
        return request.method in SAFE_METHODS

    def has_object_permission(self, request, view, obj) -> bool:
        return request.user.is_staff or obj.user_id == request.user.pk
