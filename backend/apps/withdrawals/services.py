"""
Withdrawal service layer.

All balance mutations use select_for_update() + F() expressions to guarantee
atomicity and eliminate race conditions under concurrent requests.
"""
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
def request_withdrawal(user: User, amount: Decimal, currency: str = "USD") -> Withdrawal:
    """
    Create a PENDING withdrawal and atomically debit `user.bonus_balance`.

    Steps (all within one SERIALIZABLE transaction):
    1. Lock the User row with SELECT FOR UPDATE to block concurrent requests.
    2. Re-read `bonus_balance` from the locked row (stale in-memory value is
       unreliable under concurrency).
    3. Validate amount > 0 and balance sufficient.
    4. Debit balance via UPDATE … SET bonus_balance = bonus_balance - amount.
    5. Create the Withdrawal record.

    Idempotency: retrying after a partial failure is safe because
    Withdrawal.reference has a UNIQUE constraint.

    Args:
        user:     The authenticated user requesting the payout.
        amount:   Requested amount (must be > 0 and <= bonus_balance).
        currency: ISO 4217 currency code (default 'USD').

    Returns:
        Newly created Withdrawal instance with status PENDING.

    Raises:
        InsufficientBalanceError: If balance < amount.
        ValueError:               If amount <= 0.
    """
    if amount <= Decimal("0.00"):
        raise ValueError("Withdrawal amount must be positive.")

    # Lock user row — prevents concurrent over-withdrawal
    locked_user = User.objects.select_for_update().get(pk=user.pk)

    if locked_user.bonus_balance < amount:
        raise InsufficientBalanceError(
            f"Insufficient balance: have {locked_user.bonus_balance}, "
            f"requested {amount}."
        )

    # Atomic debit using F() — no read-modify-write race
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
    """
    Approve a PENDING withdrawal.

    Balance was already debited at request time; no balance change here.
    Simply transitions status to APPROVED and records the processor.

    Raises:
        InvalidWithdrawalStateError: If the withdrawal is not PENDING.
    """
    # Lock row to prevent concurrent approve + reject
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
    """
    Reject a PENDING withdrawal and REFUND `bonus_balance`.

    Steps:
    1. Lock both Withdrawal and User rows.
    2. Validate state is PENDING.
    3. Refund balance via UPDATE … SET bonus_balance = bonus_balance + amount.
    4. Transition status to REJECTED.

    Raises:
        InvalidWithdrawalStateError: If the withdrawal is not PENDING.
    """
    withdrawal = Withdrawal.objects.select_for_update().get(pk=withdrawal.pk)

    if withdrawal.status != WithdrawalStatus.PENDING:
        raise InvalidWithdrawalStateError(
            f"Cannot reject withdrawal {withdrawal.reference!r}: "
            f"current status is {withdrawal.status!r}."
        )

    # Atomic refund
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
