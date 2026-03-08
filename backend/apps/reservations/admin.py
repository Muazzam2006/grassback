from django.contrib import admin
from django.utils.translation import gettext_lazy as _

from .models import Reservation, ReservationStatus


@admin.register(Reservation)
class ReservationAdmin(admin.ModelAdmin):
    list_display = (
        "id_short",
        "user",
        "variant",
        "quantity",
        "status",
        "expires_at",
        "created_at",
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
        "id",
        "user",
        "variant",
        "quantity",
        "status",
        "expires_at",
        "created_at",
        "updated_at",
    )
    list_select_related = ("user", "variant", "variant__product")

    @admin.display(description="ID (short)")
    def id_short(self, obj):
        return str(obj.pk)[:8]

    def has_add_permission(self, request) -> bool:
        return False

    def has_change_permission(self, request, obj=None) -> bool:
        return False

    def has_delete_permission(self, request, obj=None) -> bool:
        return False

    @admin.action(description=_("Force-expire selected ACTIVE reservations"))
    def force_expire(self, request, queryset):
        count = queryset.filter(status=ReservationStatus.ACTIVE).update(
            status=ReservationStatus.EXPIRED
        )
        self.message_user(request, f"Force-expired {count} reservation(s).")

    actions = ["force_expire"]
