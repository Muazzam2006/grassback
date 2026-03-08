from rest_framework import permissions
from .models import OrderStatus

class IsOrderOwnerOrAdmin(permissions.BasePermission):

    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated

    def has_object_permission(self, request, view, obj):
                                   
        if request.user.is_staff:
            return True

                                                   
        return obj.user == request.user


class IsOrderEditable(permissions.BasePermission):

    def has_object_permission(self, request, view, obj):
                                                      
                                                              
        if request.method in permissions.SAFE_METHODS:
            return True

                                                                    
        return obj.status in {
            OrderStatus.CREATED,
            OrderStatus.RESERVED,
            OrderStatus.CONFIRMED,
            OrderStatus.SHIPPED,
        }
