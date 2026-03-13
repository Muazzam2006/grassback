from decimal import Decimal

from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models import F
from django.utils import timezone

from .models import Withdrawal, WithdrawalStatus

User = get_user_model()


class WithdrawalError(Exception):
    """Base exception for withdrawal domain errors."""


class InsufficientBalanceError(WithdrawalError):
    """Raised when the user's bonus_balance is less than the requested amount."""


class InvalidWithdrawalStateError(WithdrawalError):
    """Raised when an operation is attempted on a withdrawal in an incompatible state."""


@transaction.atomic
def request_withdrawal(user: User, amount: Decimal, currency: str = "TJS") -> Withdrawal:
    if amount <= Decimal("0.00"):
        raise ValueError("Withdrawal amount must be positive.")

                                                         
    locked_user = User.objects.select_for_update().get(pk=user.pk)

    if locked_user.bonus_balance < amount:
        raise InsufficientBalanceError(
            f"Insufficient balance: have {locked_user.bonus_balance}, "
            f"requested {amount}."
        )

                                                        
    User.objects.filter(pk=locked_user.pk).update(
        bonus_balance=F("bonus_balance") - amount
    )

    withdrawal = Withdrawal(
        user=locked_user,
        amount=amount,
        currency=currency,
        status=WithdrawalStatus.PENDING,
    )
    withdrawal.save()
    return withdrawal


@transaction.atomic
def approve_withdrawal(withdrawal: Withdrawal, admin_user: User) -> Withdrawal:
                                                     
    withdrawal = Withdrawal.objects.select_for_update().get(pk=withdrawal.pk)

    if withdrawal.status != WithdrawalStatus.PENDING:
        raise InvalidWithdrawalStateError(
            f"Cannot approve withdrawal {withdrawal.reference!r}: "
            f"current status is {withdrawal.status!r}."
        )

    withdrawal.status = WithdrawalStatus.APPROVED
    withdrawal.processed_at = timezone.now()
    withdrawal.processed_by = admin_user
    withdrawal.save(update_fields=["status", "processed_at", "processed_by"])
    return withdrawal


@transaction.atomic
def reject_withdrawal(
    withdrawal: Withdrawal,
    admin_user: User,
    reason: str = "",
) -> Withdrawal:
    
    withdrawal = Withdrawal.objects.select_for_update().get(pk=withdrawal.pk)

    if withdrawal.status != WithdrawalStatus.PENDING:
        raise InvalidWithdrawalStateError(
            f"Cannot reject withdrawal {withdrawal.reference!r}: "
            f"current status is {withdrawal.status!r}."
        )

                   
    User.objects.filter(pk=withdrawal.user_id).update(
        bonus_balance=F("bonus_balance") + withdrawal.amount
    )

    withdrawal.status = WithdrawalStatus.REJECTED
    withdrawal.processed_at = timezone.now()
    withdrawal.processed_by = admin_user
    withdrawal.rejection_reason = reason
    withdrawal.save(update_fields=[
        "status", "processed_at", "processed_by", "rejection_reason"
    ])
    return withdrawal
