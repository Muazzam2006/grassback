from django.contrib import admin
from unfold.admin import ModelAdmin, TabularInline
from django.utils.translation import gettext_lazy as _

from .models import Courier, DeliveryAddress, DeliveryStatus, OrderDelivery
from .services import InvalidTransitionError, update_delivery_status

DeliveryAddress._meta.verbose_name = "Адрес получателя"
DeliveryAddress._meta.verbose_name_plural = "Адреса получателей"
Courier._meta.verbose_name = "Курьер"
Courier._meta.verbose_name_plural = "Курьеры"
OrderDelivery._meta.verbose_name = "Отгрузка заказа"
OrderDelivery._meta.verbose_name_plural = "Отгрузки заказов"

DELIVERY_STATUS_LABELS = {
    DeliveryStatus.PENDING: "В ожидании",
    DeliveryStatus.SHIPPED: "Отправлен",
    DeliveryStatus.DELIVERED: "Доставлен",
    DeliveryStatus.CANCELLED: "Отменен",
}


class DeliveryAddressInline(TabularInline):
    model = DeliveryAddress
    extra = 0
    readonly_fields = ("created_at", "updated_at")


@admin.register(DeliveryAddress)
class DeliveryAddressAdmin(ModelAdmin):
    list_display = (
        "user_display",
        "first_name_display",
        "last_name_display",
        "city_display",
        "is_default_display",
        "created_at_display",
    )
    list_filter = ("is_default", "region", "city")
    search_fields = ("user__phone", "first_name", "last_name", "phone", "city")
    readonly_fields = ("created_at", "updated_at")
    ordering = ("user", "-is_default")

    @admin.display(description="Пользователь", ordering="user__phone")
    def user_display(self, obj: DeliveryAddress):
        return obj.user

    @admin.display(description="Имя", ordering="first_name")
    def first_name_display(self, obj: DeliveryAddress):
        return obj.first_name

    @admin.display(description="Фамилия", ordering="last_name")
    def last_name_display(self, obj: DeliveryAddress):
        return obj.last_name

    @admin.display(description="Город", ordering="city")
    def city_display(self, obj: DeliveryAddress):
        return obj.city

    @admin.display(description="Адрес по умолчанию", ordering="is_default")
    def is_default_display(self, obj: DeliveryAddress):
        return obj.is_default

    @admin.display(description="Создан", ordering="created_at")
    def created_at_display(self, obj: DeliveryAddress):
        return obj.created_at


@admin.register(Courier)
class CourierAdmin(ModelAdmin):
    list_display = (
        "first_name_display",
        "last_name_display",
        "phone_display",
        "is_active_display",
        "created_at_display",
    )
    list_filter = ("is_active",)
    search_fields = ("first_name", "last_name", "phone")
    readonly_fields = ("created_at",)

    @admin.display(description="Имя", ordering="first_name")
    def first_name_display(self, obj: Courier):
        return obj.first_name

    @admin.display(description="Фамилия", ordering="last_name")
    def last_name_display(self, obj: Courier):
        return obj.last_name

    @admin.display(description="Телефон", ordering="phone")
    def phone_display(self, obj: Courier):
        return obj.phone

    @admin.display(boolean=True, description="Активен", ordering="is_active")
    def is_active_display(self, obj: Courier):
        return obj.is_active

    @admin.display(description="Создан", ordering="created_at")
    def created_at_display(self, obj: Courier):
        return obj.created_at


@admin.register(OrderDelivery)
class OrderDeliveryAdmin(ModelAdmin):
    list_display = (
        "order_display",
        "status_display",
        "delivery_fee_display",
        "courier_display",
        "tracking_number_display",
        "shipped_at_display",
        "delivered_at_display",
    )
    list_filter = ("status", "courier")
    search_fields = ("order__id", "tracking_number", "courier__phone")
    readonly_fields = ("order", "delivery_fee", "created_at", "updated_at")
    actions = ["action_ship", "action_deliver", "action_cancel"]
    ordering = ("-created_at",)

    @admin.display(description="Заказ", ordering="order__created_at")
    def order_display(self, obj: OrderDelivery):
        return obj.order

    @admin.display(description="Статус", ordering="status")
    def status_display(self, obj: OrderDelivery):
        return DELIVERY_STATUS_LABELS.get(obj.status, obj.status)

    @admin.display(description="Стоимость доставки", ordering="delivery_fee")
    def delivery_fee_display(self, obj: OrderDelivery):
        return obj.delivery_fee

    @admin.display(description="Курьер", ordering="courier")
    def courier_display(self, obj: OrderDelivery):
        return obj.courier

    @admin.display(description="Трек-номер", ordering="tracking_number")
    def tracking_number_display(self, obj: OrderDelivery):
        return obj.tracking_number

    @admin.display(description="Отправлен", ordering="shipped_at")
    def shipped_at_display(self, obj: OrderDelivery):
        return obj.shipped_at

    @admin.display(description="Доставлен", ordering="delivered_at")
    def delivered_at_display(self, obj: OrderDelivery):
        return obj.delivered_at

    def has_delete_permission(self, request, obj=None) -> bool:
        return False

    @admin.action(description=_("Отметить выбранные доставки как отправленные"))
    def action_ship(self, request, queryset):
        updated = 0
        for delivery in queryset.filter(status=DeliveryStatus.PENDING):
            try:
                update_delivery_status(delivery, DeliveryStatus.SHIPPED)
                updated += 1
            except InvalidTransitionError:
                pass
        self.message_user(request, f"Отправлено: {updated}")

    @admin.action(description=_("Отметить выбранные доставки как доставленные"))
    def action_deliver(self, request, queryset):
        updated = 0
        for delivery in queryset.filter(status=DeliveryStatus.SHIPPED):
            try:
                update_delivery_status(delivery, DeliveryStatus.DELIVERED)
                updated += 1
            except InvalidTransitionError:
                pass
        self.message_user(request, f"Доставлено: {updated}")

    @admin.action(description=_("Отменить выбранные доставки"))
    def action_cancel(self, request, queryset):
        updated = 0
        for delivery in queryset.filter(status__in=[DeliveryStatus.PENDING, DeliveryStatus.SHIPPED]):
            try:
                update_delivery_status(delivery, DeliveryStatus.CANCELLED)
                updated += 1
            except InvalidTransitionError:
                pass
        self.message_user(request, f"Отменено: {updated}")
