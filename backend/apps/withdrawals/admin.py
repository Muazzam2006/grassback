from django.contrib import admin
from unfold.admin import ModelAdmin
from django.utils.translation import gettext_lazy as _

from .models import Withdrawal, WithdrawalStatus
from .services import (
    InvalidWithdrawalStateError,
    approve_withdrawal,
    reject_withdrawal,
)

Withdrawal._meta.verbose_name = "Заявка на вывод"
Withdrawal._meta.verbose_name_plural = "Заявки на вывод"

WITHDRAWAL_STATUS_LABELS = {
    WithdrawalStatus.PENDING: "В ожидании",
    WithdrawalStatus.APPROVED: "Подтверждена",
    WithdrawalStatus.REJECTED: "Отклонена",
}


@admin.register(Withdrawal)
class WithdrawalAdmin(ModelAdmin):
    list_display = (
        "reference_display",
        "user_display",
        "amount_display",
        "currency_display",
        "status_display",
        "requested_at_display",
        "processed_at_display",
        "processed_by_display",
    )
    list_filter = ("status", "currency", "requested_at")
    search_fields = ("reference", "user__phone", "user__first_name", "user__last_name")
    ordering = ("-requested_at",)
    readonly_fields = (
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

    @admin.display(description="Номер заявки", ordering="reference")
    def reference_display(self, obj: Withdrawal):
        return obj.reference

    @admin.display(description="Пользователь", ordering="user__phone")
    def user_display(self, obj: Withdrawal):
        return obj.user

    @admin.display(description="Сумма", ordering="amount")
    def amount_display(self, obj: Withdrawal):
        return obj.amount

    @admin.display(description="Валюта", ordering="currency")
    def currency_display(self, obj: Withdrawal):
        return obj.currency

    @admin.display(description="Статус", ordering="status")
    def status_display(self, obj: Withdrawal):
        return WITHDRAWAL_STATUS_LABELS.get(obj.status, obj.status)

    @admin.display(description="Запрошено", ordering="requested_at")
    def requested_at_display(self, obj: Withdrawal):
        return obj.requested_at

    @admin.display(description="Обработано", ordering="processed_at")
    def processed_at_display(self, obj: Withdrawal):
        return obj.processed_at

    @admin.display(description="Обработал", ordering="processed_by")
    def processed_by_display(self, obj: Withdrawal):
        return obj.processed_by

    def has_add_permission(self, request) -> bool:
        return False                                                

    def has_delete_permission(self, request, obj=None) -> bool:
        return False                                   

    def has_change_permission(self, request, obj=None) -> bool:
        if obj and obj.status != WithdrawalStatus.PENDING:
            return False
        return request.user.is_staff

    @admin.action(description=_("Подтвердить выбранные заявки на вывод"))
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
            f"Подтверждено: {approved}. Пропущено (не в статусе ожидания): {skipped}.",
        )

    @admin.action(description=_("Отклонить выбранные заявки на вывод"))
    def action_reject(self, request, queryset):
        rejected = 0
        skipped = 0
        for withdrawal in queryset.filter(status=WithdrawalStatus.PENDING):
            try:
                reject_withdrawal(
                    withdrawal,
                    admin_user=request.user,
                    reason="Отклонено через групповое действие администратора.",
                )
                rejected += 1
            except InvalidWithdrawalStateError:
                skipped += 1
        self.message_user(
            request,
            f"Отклонено: {rejected}. Пропущено (не в статусе ожидания): {skipped}.",
        )
