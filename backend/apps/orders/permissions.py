from rest_framework import permissions
from .models import OrderStatus

class IsOrderOwnerOrAdmin(permissions.BasePermission):
    """
    Custom permission to only allow owners of an order to edit it.
    Admins can view all.
    """

    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated

    def has_object_permission(self, request, view, obj):
        # Admins can view any order
        if request.user.is_staff:
            return True

        # Users can only view/edit their own orders
        return obj.user == request.user


class IsOrderEditable(permissions.BasePermission):
    """
    Permission to prevent modification of terminal orders.
    """

    def has_object_permission(self, request, view, obj):
        # Read permissions are allowed to any request,
        # so we'll always allow GET, HEAD or OPTIONS requests.
        if request.method in permissions.SAFE_METHODS:
            return True

        # Write permissions are only allowed before terminal states.
        return obj.status in {
            OrderStatus.CREATED,
            OrderStatus.RESERVED,
            OrderStatus.CONFIRMED,
            OrderStatus.SHIPPED,
        }
