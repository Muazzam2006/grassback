from django.contrib import admin

from .models import NetworkStats, StatusThreshold


@admin.register(StatusThreshold)
class StatusThresholdAdmin(admin.ModelAdmin):
    """
    Admin interface for status promotion rules.
    Admins can edit thresholds without code deploys.
    """

    list_display = (
        "status",
        "min_personal_turnover",
        "min_team_turnover",
        "updated_at",
    )
    ordering = ("min_personal_turnover",)
    readonly_fields = ("updated_at",)

    def has_delete_permission(self, request, obj=None) -> bool:
        # Prevent accidental deletion of threshold rules.
        # Deactivate by setting high thresholds instead.
        return False


@admin.register(NetworkStats)
class NetworkStatsAdmin(admin.ModelAdmin):
    """Read-only view of cached network aggregates."""

    list_display = ("user", "team_size", "team_sales", "updated_at")
    search_fields = ("user__phone", "user__first_name", "user__last_name")
    ordering = ("-team_sales",)
    readonly_fields = ("user", "team_size", "team_sales", "updated_at")

    def has_add_permission(self, request) -> bool:
        return False

    def has_delete_permission(self, request, obj=None) -> bool:
        return False

    def has_change_permission(self, request, obj=None) -> bool:
        return False
