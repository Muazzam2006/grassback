from django.utils.translation import gettext_lazy as _
from rest_framework.permissions import BasePermission, SAFE_METHODS


class IsWithdrawalOwnerOrAdmin(BasePermission):
    """
    Object-level permission: only the withdrawal owner or an admin may access.
    All mutating actions (approve/reject) require is_staff regardless.
    """
    message = _("You do not have permission to access this withdrawal.")

    def has_object_permission(self, request, view, obj) -> bool:
        return request.user.is_staff or obj.user_id == request.user.pk


class IsAdminOnly(BasePermission):
    """Allow access only to staff users."""
    message = _("Only administrators can perform this action.")

    def has_permission(self, request, view) -> bool:
        return bool(request.user and request.user.is_staff)
