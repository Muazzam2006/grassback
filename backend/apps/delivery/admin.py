from django.contrib import admin
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from .models import Courier, DeliveryAddress, DeliveryStatus, OrderDelivery
from .services import InvalidTransitionError, update_delivery_status


class DeliveryAddressInline(admin.TabularInline):
    model = DeliveryAddress
    extra = 0
    readonly_fields = ("id", "created_at", "updated_at")


@admin.register(DeliveryAddress)
class DeliveryAddressAdmin(admin.ModelAdmin):
    list_display = ("user", "first_name", "last_name", "city", "is_default", "created_at")
    list_filter = ("is_default", "region", "city")
    search_fields = ("user__phone", "first_name", "last_name", "phone", "city")
    readonly_fields = ("id", "created_at", "updated_at")
    ordering = ("user", "-is_default")


@admin.register(Courier)
class CourierAdmin(admin.ModelAdmin):
    list_display = ("first_name", "last_name", "phone", "is_active", "created_at")
    list_filter = ("is_active",)
    search_fields = ("first_name", "last_name", "phone")
    readonly_fields = ("id", "created_at")
    list_editable = ("is_active",)


@admin.register(OrderDelivery)
class OrderDeliveryAdmin(admin.ModelAdmin):
    list_display = (
        "order", "status", "delivery_fee", "courier",
        "tracking_number", "shipped_at", "delivered_at",
    )
    list_filter = ("status", "courier")
    search_fields = ("order__id", "tracking_number", "courier__phone")
    readonly_fields = ("id", "order", "delivery_fee", "created_at", "updated_at")
    actions = ["action_ship", "action_deliver", "action_cancel"]
    ordering = ("-created_at",)

    def has_delete_permission(self, request, obj=None) -> bool:
        return False

    @admin.action(description=_("Mark selected deliveries as SHIPPED"))
    def action_ship(self, request, queryset):
        updated = 0
        for delivery in queryset.filter(status=DeliveryStatus.PENDING):
            try:
                update_delivery_status(delivery, DeliveryStatus.SHIPPED)
                updated += 1
            except InvalidTransitionError:
                pass
        self.message_user(request, _(f"Shipped: {updated}"))

    @admin.action(description=_("Mark selected deliveries as DELIVERED"))
    def action_deliver(self, request, queryset):
        updated = 0
        for delivery in queryset.filter(status=DeliveryStatus.SHIPPED):
            try:
                update_delivery_status(delivery, DeliveryStatus.DELIVERED)
                updated += 1
            except InvalidTransitionError:
                pass
        self.message_user(request, _(f"Delivered: {updated}"))

    @admin.action(description=_("Cancel selected deliveries"))
    def action_cancel(self, request, queryset):
        updated = 0
        for delivery in queryset.filter(status__in=[DeliveryStatus.PENDING, DeliveryStatus.SHIPPED]):
            try:
                update_delivery_status(delivery, DeliveryStatus.CANCELLED)
                updated += 1
            except InvalidTransitionError:
                pass
        self.message_user(request, _(f"Cancelled: {updated}"))
