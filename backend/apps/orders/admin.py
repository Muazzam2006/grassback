from django.contrib import admin

from .models import Order, OrderItem, OrderLifecycleLog, OrderStatus
from .services import (
    OrderTransitionError,
    cancel_order,
    confirm_order,
    deliver_order,
    ship_order,
)


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = (
        "product",
        "variant",
        "reservation",
        "product_name_snapshot",
        "product_price_snapshot",
        "quantity",
        "line_total",
    )
    can_delete = False


class OrderLifecycleLogInline(admin.TabularInline):
    model = OrderLifecycleLog
    extra = 0
    readonly_fields = ("from_status", "to_status", "changed_by", "note", "created_at")
    can_delete = False
    ordering = ("created_at",)


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = (
        "id", "user", "status",
        "total_amount", "delivery_fee", "grand_total_display",
        "currency", "delivery_address", "created_at",
    )
    list_filter = ("status", "currency", "created_at")
    search_fields = ("id", "user__phone", "user__first_name", "user__last_name")
    ordering = ("-created_at",)
    readonly_fields = (
        "id", "user", "status",
        "total_amount", "delivery_fee", "grand_total_display",
        "currency", "delivery_address", "created_at", "updated_at",
    )
    list_select_related = ("user", "delivery_address")
    inlines = [OrderItemInline, OrderLifecycleLogInline]

    @admin.display(description="Grand Total")
    def grand_total_display(self, obj: Order):
        return obj.grand_total

    def has_add_permission(self, request) -> bool:
        return False

    def has_delete_permission(self, request, obj=None) -> bool:
        if obj and obj.status in (OrderStatus.DELIVERED, OrderStatus.CANCELLED):
            return False
        return super().has_delete_permission(request, obj)

    def has_change_permission(self, request, obj=None) -> bool:
        if obj and obj.status in (OrderStatus.DELIVERED, OrderStatus.CANCELLED):
            return False
        return super().has_change_permission(request, obj)
                                 

    @admin.action(description="✔ Confirm selected RESERVED orders")
    def action_confirm(self, request, queryset):
        ok, fail = 0, 0
        for order in queryset:
            try:
                confirm_order(order, admin_user=request.user)
                ok += 1
            except OrderTransitionError:
                fail += 1
        if ok:
            self.message_user(request, f"Confirmed {ok} order(s).")
        if fail:
            self.message_user(request, f"Skipped {fail} order(s) — invalid status.", level="warning")

    @admin.action(description="🚚 Ship selected CONFIRMED orders")
    def action_ship(self, request, queryset):
        ok, fail = 0, 0
        for order in queryset:
            try:
                ship_order(order, admin_user=request.user)
                ok += 1
            except OrderTransitionError:
                fail += 1
        if ok:
            self.message_user(request, f"Shipped {ok} order(s).")
        if fail:
            self.message_user(request, f"Skipped {fail} order(s) — invalid status.", level="warning")

    @admin.action(description="✅ Mark selected SHIPPED orders as DELIVERED")
    def action_deliver(self, request, queryset):
        ok, fail = 0, 0
        for order in queryset:
            try:
                deliver_order(order, admin_user=request.user)
                ok += 1
            except (OrderTransitionError, ValueError):
                fail += 1
        if ok:
            self.message_user(request, f"Delivered {ok} order(s).")
        if fail:
            self.message_user(request, f"Skipped {fail} order(s) — invalid status.", level="warning")

    @admin.action(description="✖ Cancel selected orders")
    def action_cancel(self, request, queryset):
        ok, fail = 0, 0
        for order in queryset:
            try:
                cancel_order(order, changed_by=request.user, note="Cancelled by admin.")
                ok += 1
            except OrderTransitionError:
                fail += 1
        if ok:
            self.message_user(request, f"Cancelled {ok} order(s).")
        if fail:
            self.message_user(request, f"Skipped {fail} order(s) — already terminal.", level="warning")

    actions = ["action_confirm", "action_ship", "action_deliver", "action_cancel"]


@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = (
        "order", "product", "variant",
        "product_name_snapshot", "product_price_snapshot",
        "quantity", "line_total",
    )
    readonly_fields = (
        "order", "product", "variant", "reservation",
        "product_name_snapshot", "product_price_snapshot",
        "quantity", "line_total",
    )

    def has_add_permission(self, request) -> bool:
        return False

    def has_delete_permission(self, request, obj=None) -> bool:
        return False

    def has_change_permission(self, request, obj=None) -> bool:
        return False


@admin.register(OrderLifecycleLog)
class OrderLifecycleLogAdmin(admin.ModelAdmin):
    list_display = ("order", "from_status", "to_status", "changed_by", "created_at")
    list_filter = ("to_status", "from_status")
    readonly_fields = ("id", "order", "from_status", "to_status", "changed_by", "note", "created_at")

    def has_add_permission(self, request) -> bool:
        return False

    def has_change_permission(self, request, obj=None) -> bool:
        return False

    def has_delete_permission(self, request, obj=None) -> bool:
        return False
