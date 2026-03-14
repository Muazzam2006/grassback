from django.contrib import admin
from unfold.admin import ModelAdmin

from .models import Bonus, BonusStatus, BonusType, CalculationType, MLMRule

MLMRule._meta.verbose_name = "Правило начисления"
MLMRule._meta.verbose_name_plural = "Правила начисления"
Bonus._meta.verbose_name = "Начисление бонуса"
Bonus._meta.verbose_name_plural = "Начисления бонусов"

MLMRule._meta.get_field("agent_status").verbose_name = "Статус агента"
MLMRule._meta.get_field("agent_status").choices = [
    ("NEW", "Новый"),
    ("BRONZE", "Бронза"),
    ("SILVER", "Серебро"),
    ("GOLD", "Золото"),
]
MLMRule._meta.get_field("calculation_type").verbose_name = "Тип расчета"
MLMRule._meta.get_field("calculation_type").choices = [
    (CalculationType.PERCENT, "Процент"),
    (CalculationType.FIXED, "Фиксированная сумма"),
]
MLMRule._meta.get_field("is_active").verbose_name = "Активно"

Bonus._meta.get_field("status").verbose_name = "Статус"
Bonus._meta.get_field("status").choices = [
    (BonusStatus.PENDING, "В ожидании"),
    (BonusStatus.CONFIRMED, "Подтвержден"),
]
Bonus._meta.get_field("bonus_type").verbose_name = "Тип бонуса"
Bonus._meta.get_field("bonus_type").choices = [
    (BonusType.PERSONAL, "Личный"),
    (BonusType.TEAM, "Командный"),
]
Bonus._meta.get_field("calculation_type_snapshot").verbose_name = "Тип расчета"
Bonus._meta.get_field("calculation_type_snapshot").choices = [
    (CalculationType.PERCENT, "Процент"),
    (CalculationType.FIXED, "Фиксированная сумма"),
]


@admin.register(MLMRule)
class MLMRuleAdmin(ModelAdmin):
    list_display = (
        "agent_status_display",
        "level_display",
        "calculation_type_display",
        "value_display",
        "is_active_display",
        "created_at_display",
    )
    list_filter = ("agent_status", "calculation_type", "is_active")
    search_fields = ("agent_status",)
    ordering = ("agent_status", "level")

    @admin.display(description="Статус агента", ordering="agent_status")
    def agent_status_display(self, obj: MLMRule):
        status_map = {
            "NEW": "Новый",
            "BRONZE": "Бронза",
            "SILVER": "Серебро",
            "GOLD": "Золото",
        }
        return status_map.get(obj.agent_status, obj.agent_status)

    @admin.display(description="Уровень", ordering="level")
    def level_display(self, obj: MLMRule):
        return obj.level

    @admin.display(description="Тип расчета", ordering="calculation_type")
    def calculation_type_display(self, obj: MLMRule):
        calc_map = {
            CalculationType.PERCENT: "Процент",
            CalculationType.FIXED: "Фиксированная сумма",
        }
        return calc_map.get(obj.calculation_type, obj.calculation_type)

    @admin.display(description="Значение", ordering="value")
    def value_display(self, obj: MLMRule):
        return obj.value

    @admin.display(boolean=True, description="Активно", ordering="is_active")
    def is_active_display(self, obj: MLMRule):
        return obj.is_active

    @admin.display(description="Создано", ordering="created_at")
    def created_at_display(self, obj: MLMRule):
        return obj.created_at


@admin.register(Bonus)
class BonusAdmin(ModelAdmin):
    list_display = (
        "recipient_display",
        "source_user_display",
        "order_display",
        "level_display",
        "bonus_type_display",
        "calculation_type_display",
        "applied_value_display",
        "amount_display",
        "status_display",
        "created_at_display",
    )
    list_filter = ("status", "bonus_type", "calculation_type_snapshot")
    search_fields = ("user__phone", "source_user__phone", "order__id")
    readonly_fields = tuple(f.name for f in Bonus._meta.fields if f.name != "id")
    ordering = ("-created_at",)

    def has_add_permission(self, request) -> bool:
        return False

    def has_change_permission(self, request, obj=None) -> bool:
        return False

    def has_delete_permission(self, request, obj=None) -> bool:
        return False

    @admin.display(description="Пользователь", ordering="user__phone")
    def recipient_display(self, obj: Bonus):
        full_name = obj.user.get_full_name()
        if full_name:
            return f"{full_name} ({obj.user.phone})"
        return obj.user.phone

    @admin.display(description="Источник", ordering="source_user__phone")
    def source_user_display(self, obj: Bonus):
        full_name = obj.source_user.get_full_name()
        if full_name:
            return f"{full_name} ({obj.source_user.phone})"
        return obj.source_user.phone

    @admin.display(description="Заказ", ordering="order__created_at")
    def order_display(self, obj: Bonus):
        status_map = {
            "CREATED": "Создан",
            "RESERVED": "Забронирован",
            "CONFIRMED": "Подтвержден",
            "SHIPPED": "Отправлен",
            "DELIVERED": "Доставлен",
            "CANCELLED": "Отменен",
        }
        status_label = status_map.get(obj.order.status, obj.order.status)
        return f"{status_label}, {obj.order.created_at:%d.%m.%Y %H:%M}"

    @admin.display(description="Тип бонуса", ordering="bonus_type")
    def bonus_type_display(self, obj: Bonus):
        type_map = {
            "PERSONAL": "Личный",
            "TEAM": "Командный",
        }
        return type_map.get(obj.bonus_type, obj.bonus_type)

    @admin.display(description="Тип расчета", ordering="calculation_type_snapshot")
    def calculation_type_display(self, obj: Bonus):
        calc_map = {
            "PERCENT": "Процент",
            "FIXED": "Фиксированная сумма",
        }
        return calc_map.get(obj.calculation_type_snapshot, obj.calculation_type_snapshot)

    @admin.display(description="Статус", ordering="status")
    def status_display(self, obj: Bonus):
        status_map = {
            "PENDING": "В ожидании",
            "CONFIRMED": "Подтвержден",
        }
        return status_map.get(obj.status, obj.status)

    @admin.display(description="Уровень", ordering="level")
    def level_display(self, obj: Bonus):
        return obj.level

    @admin.display(description="Примененное значение", ordering="applied_value_snapshot")
    def applied_value_display(self, obj: Bonus):
        return obj.applied_value_snapshot

    @admin.display(description="Сумма", ordering="amount")
    def amount_display(self, obj: Bonus):
        return obj.amount

    @admin.display(description="Создан", ordering="created_at")
    def created_at_display(self, obj: Bonus):
        return obj.created_at
