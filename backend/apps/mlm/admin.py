from django.contrib import admin
from unfold.admin import ModelAdmin

from .models import NetworkStats, StatusThreshold

StatusThreshold._meta.verbose_name = "Порог карьерного статуса"
StatusThreshold._meta.verbose_name_plural = "Пороги карьерных статусов"
NetworkStats._meta.verbose_name = "Сводка по структуре"
NetworkStats._meta.verbose_name_plural = "Сводки по структуре"


@admin.register(StatusThreshold)
class StatusThresholdAdmin(ModelAdmin):

    list_display = (
        "status_display",
        "min_personal_turnover_display",
        "min_team_turnover_display",
        "updated_at_display",
    )
    ordering = ("min_personal_turnover",)
    readonly_fields = ()

    @admin.display(description="Статус", ordering="status")
    def status_display(self, obj: StatusThreshold):
        status_map = {
            "BRONZE": "Бронза",
            "SILVER": "Серебро",
            "GOLD": "Золото",
        }
        return status_map.get(obj.status, obj.status)

    @admin.display(description="Мин. личный оборот", ordering="min_personal_turnover")
    def min_personal_turnover_display(self, obj: StatusThreshold):
        return obj.min_personal_turnover

    @admin.display(description="Мин. командный оборот", ordering="min_team_turnover")
    def min_team_turnover_display(self, obj: StatusThreshold):
        return obj.min_team_turnover

    @admin.display(description="Обновлено", ordering="updated_at")
    def updated_at_display(self, obj: StatusThreshold):
        return obj.updated_at

    def has_delete_permission(self, request, obj=None) -> bool:                                                         
        return False


@admin.register(NetworkStats)
class NetworkStatsAdmin(ModelAdmin):

    list_display = (
        "user_display",
        "team_size_display",
        "team_sales_display",
        "updated_at_display",
    )
    search_fields = ("user__phone", "user__first_name", "user__last_name")
    ordering = ("-team_sales",)
    readonly_fields = ("user", "team_size", "team_sales")

    @admin.display(description="Пользователь", ordering="user__phone")
    def user_display(self, obj: NetworkStats):
        return obj.user

    @admin.display(description="Размер структуры", ordering="team_size")
    def team_size_display(self, obj: NetworkStats):
        return obj.team_size

    @admin.display(description="Оборот структуры", ordering="team_sales")
    def team_sales_display(self, obj: NetworkStats):
        return obj.team_sales

    @admin.display(description="Обновлено", ordering="updated_at")
    def updated_at_display(self, obj: NetworkStats):
        return obj.updated_at

    def has_add_permission(self, request) -> bool:
        return False

    def has_delete_permission(self, request, obj=None) -> bool:
        return False

    def has_change_permission(self, request, obj=None) -> bool:
        return False

    def get_model_perms(self, request):
        return {}
