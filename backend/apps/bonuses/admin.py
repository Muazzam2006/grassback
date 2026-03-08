from django.contrib import admin

from .models import Bonus, BonusStatus, CalculationType, MLMRule


@admin.register(MLMRule)
class MLMRuleAdmin(admin.ModelAdmin):
    list_display = (
        "agent_status", "level", "calculation_type", "value", "is_active", "created_at"
    )
    list_filter = ("agent_status", "calculation_type", "is_active")
    search_fields = ("agent_status",)
    ordering = ("agent_status", "level")
    readonly_fields = ("id", "created_at")
    list_editable = ("is_active",)


@admin.register(Bonus)
class BonusAdmin(admin.ModelAdmin):
    list_display = (
        "user", "source_user", "order", "level", "bonus_type",
        "calculation_type_snapshot", "applied_value_snapshot", "amount", "status", "created_at",
    )
    list_filter = ("status", "bonus_type", "calculation_type_snapshot")
    search_fields = ("user__phone", "source_user__phone", "order__id")
    readonly_fields = tuple(f.name for f in Bonus._meta.fields)
    ordering = ("-created_at",)

    def has_add_permission(self, request) -> bool:
        return False

    def has_change_permission(self, request, obj=None) -> bool:
        return False

    def has_delete_permission(self, request, obj=None) -> bool:
        return False
