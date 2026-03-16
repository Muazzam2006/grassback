from django.contrib import admin, messages
from unfold.admin import ModelAdmin, TabularInline, StackedInline

from .models import Order, OrderItem, OrderLifecycleLog, OrderStatus
from .services import (
    OrderTransitionError,
    cancel_order,
    confirm_order,
    deliver_order,
    ship_order,
    transition_order_status,
)

Order._meta.verbose_name = "Заказ"
Order._meta.verbose_name_plural = "Заказы"
OrderItem._meta.verbose_name = "Позиция заказа"
OrderItem._meta.verbose_name_plural = "Позиции заказа"
OrderLifecycleLog._meta.verbose_name = "История заказа"
OrderLifecycleLog._meta.verbose_name_plural = "История заказов"

_ORDER_STATUS_CHOICES_RU = [
    (OrderStatus.CREATED, "Создан"),
    (OrderStatus.RESERVED, "Забронирован"),
    (OrderStatus.CONFIRMED, "Подтвержден"),
    (OrderStatus.SHIPPED, "Отправлен"),
    (OrderStatus.DELIVERED, "Доставлен"),
    (OrderStatus.CANCELLED, "Отменен"),
]

Order._meta.get_field("status").verbose_name = "Статус"
Order._meta.get_field("status").choices = _ORDER_STATUS_CHOICES_RU
Order._meta.get_field("delivery_fee").verbose_name = "Стоимость доставки"
Order._meta.get_field("currency").verbose_name = "Валюта"
Order._meta.get_field("created_at").verbose_name = "Создан"

OrderLifecycleLog._meta.get_field("from_status").verbose_name = "Статус до"
OrderLifecycleLog._meta.get_field("to_status").verbose_name = "Статус после"
OrderLifecycleLog._meta.get_field("from_status").choices = _ORDER_STATUS_CHOICES_RU
OrderLifecycleLog._meta.get_field("to_status").choices = _ORDER_STATUS_CHOICES_RU


ORDER_STATUS_LABELS = {
    OrderStatus.CREATED: "Создан",
    OrderStatus.RESERVED: "Забронирован",
    OrderStatus.CONFIRMED: "Подтвержден",
    OrderStatus.SHIPPED: "Отправлен",
    OrderStatus.DELIVERED: "Доставлен",
    OrderStatus.CANCELLED: "Отменен",
}


class OrderItemInline(TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = (
        "product_display",
        "variant_display",
        "reservation_display",
        "product_name_snapshot_display",
        "product_price_snapshot_display",
        "quantity_display",
        "line_total_display",
    )
    fields = readonly_fields
    can_delete = False

    @admin.display(description="Товар", ordering="product__name")
    def product_display(self, obj: OrderItem):
        return obj.product

    @admin.display(description="Вариант", ordering="variant__sku")
    def variant_display(self, obj: OrderItem):
        return obj.variant

    @admin.display(description="Источник резерва", ordering="reservation")
    def reservation_display(self, obj: OrderItem):
        reservation = obj.reservation
        if reservation is None:
            return "—"

        status_choices = dict(reservation._meta.get_field("status").choices)
        status_label = status_choices.get(reservation.status, reservation.status)
        variant_sku = reservation.variant.sku if reservation.variant_id else "—"
        return f"Резерв {str(reservation.id)[:8]} · {variant_sku} · {reservation.quantity} шт. · {status_label}"

    @admin.display(description="Название товара", ordering="product_name_snapshot")
    def product_name_snapshot_display(self, obj: OrderItem):
        return obj.product_name_snapshot

    @admin.display(description="Цена товара", ordering="product_price_snapshot")
    def product_price_snapshot_display(self, obj: OrderItem):
        return obj.product_price_snapshot

    @admin.display(description="Количество", ordering="quantity")
    def quantity_display(self, obj: OrderItem):
        return obj.quantity

    @admin.display(description="Сумма", ordering="line_total")
    def line_total_display(self, obj: OrderItem):
        return obj.line_total


class OrderLifecycleLogInline(TabularInline):
    model = OrderLifecycleLog
    extra = 0
    readonly_fields = (
        "from_status_display",
        "to_status_display",
        "changed_by_display",
        "note_display",
    )
    fields = readonly_fields
    can_delete = False
    ordering = ("created_at",)

    @admin.display(description="Статус до", ordering="from_status")
    def from_status_display(self, obj: OrderLifecycleLog):
        return ORDER_STATUS_LABELS.get(obj.from_status, obj.from_status or "-")

    @admin.display(description="Статус после", ordering="to_status")
    def to_status_display(self, obj: OrderLifecycleLog):
        return ORDER_STATUS_LABELS.get(obj.to_status, obj.to_status)

    @admin.display(description="Кто изменил", ordering="changed_by")
    def changed_by_display(self, obj: OrderLifecycleLog):
        return obj.changed_by

    @admin.display(description="Комментарий", ordering="note")
    def note_display(self, obj: OrderLifecycleLog):
        return obj.note

    @admin.display(description="Дата изменения", ordering="created_at")
    def created_at_display(self, obj: OrderLifecycleLog):
        return obj.created_at


@admin.register(Order)
class OrderAdmin(ModelAdmin):
    list_display = (
        "user_display",
        "status_display",
        "total_amount_display",
        "delivery_fee_display",
        "grand_total_display",
        "currency_display",
        "delivery_address_display",
        "created_at_display",
    )
    list_filter = ("status", "currency", "created_at")
    search_fields = ("id", "user__phone", "user__first_name", "user__last_name")
    ordering = ("-created_at",)
    readonly_fields = (
        "user",
        "total_amount", "grand_total_display",
        "currency", "delivery_address",
    )
    list_select_related = ("user", "delivery_address")
    inlines = [OrderItemInline, OrderLifecycleLogInline]

    @admin.display(description="Итого")
    def grand_total_display(self, obj: Order):
        return obj.grand_total

    @admin.display(description="Пользователь", ordering="user__phone")
    def user_display(self, obj: Order):
        return obj.user

    @admin.display(description="Статус", ordering="status")
    def status_display(self, obj: Order):
        return ORDER_STATUS_LABELS.get(obj.status, obj.status)

    @admin.display(description="Сумма товаров", ordering="total_amount")
    def total_amount_display(self, obj: Order):
        return obj.total_amount

    @admin.display(description="Стоимость доставки", ordering="delivery_fee")
    def delivery_fee_display(self, obj: Order):
        return obj.delivery_fee

    @admin.display(description="Валюта", ordering="currency")
    def currency_display(self, obj: Order):
        return obj.currency

    @admin.display(description="Адрес доставки", ordering="delivery_address")
    def delivery_address_display(self, obj: Order):
        return obj.delivery_address

    @admin.display(description="Создан", ordering="created_at")
    def created_at_display(self, obj: Order):
        return obj.created_at

    def save_model(self, request, obj, form, change):
        if not change:
            super().save_model(request, obj, form, change)
            return

        current = Order.objects.get(pk=obj.pk)
        new_status = form.cleaned_data.get("status", current.status)
        new_delivery_fee = form.cleaned_data.get("delivery_fee", current.delivery_fee)

        updated_order = current

        if new_status != current.status:
            try:
                if new_status == OrderStatus.CANCELLED:
                    updated_order = cancel_order(
                        current,
                        changed_by=request.user,
                        note="Отменено администратором в карточке заказа.",
                    )
                else:
                    updated_order = transition_order_status(
                        current,
                        new_status,
                        changed_by=request.user,
                        note="Статус изменен администратором в карточке заказа.",
                    )
                self.message_user(request, "Статус заказа обновлен.", level=messages.SUCCESS)
            except OrderTransitionError as exc:
                if new_status == OrderStatus.CANCELLED:
                    self.message_user(request, f"Статус не изменен: {exc}", level=messages.ERROR)
                else:
                    old_status = current.status
                    current.status = new_status
                    current.save(update_fields=["status", "updated_at"])
                    OrderLifecycleLog.objects.create(
                        order=current,
                        from_status=old_status,
                        to_status=new_status,
                        changed_by=request.user,
                        note="Статус изменен администратором вручную.",
                    )
                    updated_order = current
                    self.message_user(
                        request,
                        "Статус обновлен вручную (вне стандартного перехода).",
                        level=messages.WARNING,
                    )

        if new_delivery_fee != updated_order.delivery_fee:
            updated_order.delivery_fee = new_delivery_fee
            updated_order.save(update_fields=["delivery_fee", "updated_at"])
            self.message_user(request, "Стоимость доставки обновлена.", level=messages.SUCCESS)

    def has_add_permission(self, request) -> bool:
        return False

    def has_delete_permission(self, request, obj=None) -> bool:
        if obj and obj.status in (OrderStatus.DELIVERED, OrderStatus.CANCELLED):
            return False
        return super().has_delete_permission(request, obj)

    def has_change_permission(self, request, obj=None) -> bool:
        return super().has_change_permission(request, obj)
                                 

    @admin.action(description="Подтвердить выбранные заказы")
    def action_confirm(self, request, queryset):
        ok, fail = 0, 0
        for order in queryset:
            try:
                confirm_order(order, admin_user=request.user)
                ok += 1
            except OrderTransitionError:
                fail += 1
        if ok:
            self.message_user(request, f"Подтверждено заказов: {ok}.")
        if fail:
            self.message_user(request, f"Пропущено заказов: {fail} (некорректный статус).", level="warning")

    @admin.action(description="Передать в доставку выбранные заказы")
    def action_ship(self, request, queryset):
        ok, fail = 0, 0
        for order in queryset:
            try:
                ship_order(order, admin_user=request.user)
                ok += 1
            except OrderTransitionError:
                fail += 1
        if ok:
            self.message_user(request, f"Передано в доставку: {ok}.")
        if fail:
            self.message_user(request, f"Пропущено заказов: {fail} (некорректный статус).", level="warning")

    @admin.action(description="Отметить выбранные заказы как доставленные")
    def action_deliver(self, request, queryset):
        ok, fail = 0, 0
        for order in queryset:
            try:
                deliver_order(order, admin_user=request.user)
                ok += 1
            except (OrderTransitionError, ValueError):
                fail += 1
        if ok:
            self.message_user(request, f"Доставлено заказов: {ok}.")
        if fail:
            self.message_user(request, f"Пропущено заказов: {fail} (некорректный статус).", level="warning")

    @admin.action(description="Отменить выбранные заказы")
    def action_cancel(self, request, queryset):
        ok, fail = 0, 0
        for order in queryset:
            try:
                cancel_order(order, changed_by=request.user, note="Отменено администратором.")
                ok += 1
            except OrderTransitionError:
                fail += 1
        if ok:
            self.message_user(request, f"Отменено заказов: {ok}.")
        if fail:
            self.message_user(request, f"Пропущено заказов: {fail} (уже финальный статус).", level="warning")

    actions = ["action_confirm", "action_ship", "action_deliver", "action_cancel"]


@admin.register(OrderItem)
class OrderItemAdmin(ModelAdmin):
    list_display = (
        "order_display",
        "product_display",
        "variant_display",
        "product_name_display",
        "product_price_display",
        "quantity_display",
        "line_total_display",
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

    def get_model_perms(self, request):
        return {}

    @admin.display(description="Заказ", ordering="order__created_at")
    def order_display(self, obj: OrderItem):
        return obj.order

    @admin.display(description="Товар", ordering="product__name")
    def product_display(self, obj: OrderItem):
        return obj.product

    @admin.display(description="Вариант", ordering="variant__sku")
    def variant_display(self, obj: OrderItem):
        return obj.variant

    @admin.display(description="Название товара", ordering="product_name_snapshot")
    def product_name_display(self, obj: OrderItem):
        return obj.product_name_snapshot

    @admin.display(description="Цена", ordering="product_price_snapshot")
    def product_price_display(self, obj: OrderItem):
        return obj.product_price_snapshot

    @admin.display(description="Количество", ordering="quantity")
    def quantity_display(self, obj: OrderItem):
        return obj.quantity

    @admin.display(description="Сумма", ordering="line_total")
    def line_total_display(self, obj: OrderItem):
        return obj.line_total


@admin.register(OrderLifecycleLog)
class OrderLifecycleLogAdmin(ModelAdmin):
    list_display = (
        "order_display",
        "from_status_display",
        "to_status_display",
        "changed_by_display",
        "created_at_display",
    )
    list_filter = ("to_status", "from_status")
    readonly_fields = ("order", "from_status", "to_status", "changed_by", "note")

    @admin.display(description="Заказ", ordering="order__created_at")
    def order_display(self, obj: OrderLifecycleLog):
        return obj.order

    @admin.display(description="Статус до", ordering="from_status")
    def from_status_display(self, obj: OrderLifecycleLog):
        return ORDER_STATUS_LABELS.get(obj.from_status, obj.from_status or "-")

    @admin.display(description="Статус после", ordering="to_status")
    def to_status_display(self, obj: OrderLifecycleLog):
        return ORDER_STATUS_LABELS.get(obj.to_status, obj.to_status)

    @admin.display(description="Кто изменил", ordering="changed_by")
    def changed_by_display(self, obj: OrderLifecycleLog):
        return obj.changed_by

    @admin.display(description="Дата изменения", ordering="created_at")
    def created_at_display(self, obj: OrderLifecycleLog):
        return obj.created_at

    def has_add_permission(self, request) -> bool:
        return False

    def has_change_permission(self, request, obj=None) -> bool:
        return False

    def has_delete_permission(self, request, obj=None) -> bool:
        return False

    def get_model_perms(self, request):
        return {}
