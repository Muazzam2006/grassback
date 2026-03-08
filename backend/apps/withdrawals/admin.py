from django.contrib import admin
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from .models import Withdrawal, WithdrawalStatus
from .services import (
    InvalidWithdrawalStateError,
    approve_withdrawal,
    reject_withdrawal,
)


@admin.register(Withdrawal)
class WithdrawalAdmin(admin.ModelAdmin):
    list_display = (
        "reference",
        "user",
        "amount",
        "currency",
        "status",
        "requested_at",
        "processed_at",
        "processed_by",
    )
    list_filter = ("status", "currency", "requested_at")
    search_fields = ("reference", "user__phone", "user__first_name", "user__last_name")
    ordering = ("-requested_at",)
    readonly_fields = (
        "id",
        "reference",
        "user",
        "amount",
        "currency",
        "requested_at",
        "processed_at",
        "processed_by",
    )
    date_hierarchy = "requested_at"
    actions = ["action_approve", "action_reject"]

    def has_add_permission(self, request) -> bool:
        return False  # Withdrawals are created through the API only

    def has_delete_permission(self, request, obj=None) -> bool:
        return False  # Financial records are permanent

    def has_change_permission(self, request, obj=None) -> bool:
        if obj and obj.status != WithdrawalStatus.PENDING:
            return False
        return request.user.is_staff

    @admin.action(description=_("Approve selected pending withdrawals"))
    def action_approve(self, request, queryset):
        approved = 0
        skipped = 0
        for withdrawal in queryset.filter(status=WithdrawalStatus.PENDING):
            try:
                approve_withdrawal(withdrawal, admin_user=request.user)
                approved += 1
            except InvalidWithdrawalStateError:
                skipped += 1
        self.message_user(
            request,
            f"Approved: {approved}. Skipped (non-pending): {skipped}.",
        )

    @admin.action(description=_("Reject selected pending withdrawals (no reason)"))
    def action_reject(self, request, queryset):
        rejected = 0
        skipped = 0
        for withdrawal in queryset.filter(status=WithdrawalStatus.PENDING):
            try:
                reject_withdrawal(
                    withdrawal,
                    admin_user=request.user,
                    reason="Rejected via admin bulk action.",
                )
                rejected += 1
            except InvalidWithdrawalStateError:
                skipped += 1
        self.message_user(
            request,
            f"Rejected: {rejected}. Skipped (non-pending): {skipped}.",
        )
