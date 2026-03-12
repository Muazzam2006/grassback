from django.contrib import admin
from django.utils.translation import gettext_lazy as _

from .models import Reservation, ReservationStatus

Reservation._meta.verbose_name = "Резерв товара"
Reservation._meta.verbose_name_plural = "Резервы товаров"

RESERVATION_STATUS_LABELS = {
    ReservationStatus.ACTIVE: "Активен",
    ReservationStatus.EXPIRED: "Истек",
    ReservationStatus.CONVERTED: "Преобразован в заказ",
    ReservationStatus.CANCELLED: "Отменен",
}


@admin.register(Reservation)
class ReservationAdmin(admin.ModelAdmin):
    list_display = (
        "user_display",
        "variant_display",
        "quantity_display",
        "status_display",
        "expires_at_display",
        "created_at_display",
    )
    list_filter = ("status", "created_at")
    search_fields = (
        "user__phone",
        "user__first_name",
        "user__last_name",
        "variant__sku",
    )
    ordering = ("-created_at",)
    readonly_fields = (
        "user",
        "variant",
        "quantity",
        "status",
        "expires_at",
        "created_at",
        "updated_at",
    )
    list_select_related = ("user", "variant", "variant__product")

    @admin.display(description="Пользователь", ordering="user__phone")
    def user_display(self, obj: Reservation):
        return obj.user

    @admin.display(description="Вариант", ordering="variant__sku")
    def variant_display(self, obj: Reservation):
        return obj.variant

    @admin.display(description="Количество", ordering="quantity")
    def quantity_display(self, obj: Reservation):
        return obj.quantity

    @admin.display(description="Статус", ordering="status")
    def status_display(self, obj: Reservation):
        return RESERVATION_STATUS_LABELS.get(obj.status, obj.status)

    @admin.display(description="Действует до", ordering="expires_at")
    def expires_at_display(self, obj: Reservation):
        return obj.expires_at

    @admin.display(description="Создан", ordering="created_at")
    def created_at_display(self, obj: Reservation):
        return obj.created_at

    def has_add_permission(self, request) -> bool:
        return False

    def has_change_permission(self, request, obj=None) -> bool:
        return False

    def has_delete_permission(self, request, obj=None) -> bool:
        return False

    @admin.action(description=_("Принудительно завершить выбранные активные брони"))
    def force_expire(self, request, queryset):
        count = queryset.filter(status=ReservationStatus.ACTIVE).update(
            status=ReservationStatus.EXPIRED
        )
        self.message_user(request, f"Принудительно завершено бронирований: {count}.")

    actions = ["force_expire"]
