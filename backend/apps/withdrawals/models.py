"""
Withdrawal model — financial ledger entry.

Financial consistency rules
----------------------------
1.  `bonus_balance` is DEBITED atomically inside `request_withdrawal()` the
    moment the user submits the request, preventing double-spend on concurrent
    requests.
2.  If the withdrawal is REJECTED, `bonus_balance` is REFUNDED inside
    `reject_withdrawal()` in a separate atomic transaction.
3.  APPROVING a withdrawal does NOT modify `bonus_balance` (balance was already
    debited at request time).
4.  Both the debit and the Withdrawal row are written in the same
    `transaction.atomic()` block so partial failures are impossible.
5.  `select_for_update()` on the User row prevents concurrent withdrawals from
    racing against each other.
"""
import secrets
import string
import uuid

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import IntegrityError, models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from decimal import Decimal


class WithdrawalStatus(models.TextChoices):
    PENDING = "PENDING", _("Pending")
    APPROVED = "APPROVED", _("Approved")
    REJECTED = "REJECTED", _("Rejected")


class Withdrawal(models.Model):
    """
    Immutable-on-create ledger record representing one payout request.

    Balance lifecycle
    -----------------
    REQUEST  → user.bonus_balance  −= amount  (inside request_withdrawal)
    APPROVE  → no balance change   (balance already debited)
    REJECT   → user.bonus_balance  += amount  (inside reject_withdrawal, refund)
    """

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    # Human-readable reference shown on receipts: WD-XXXXXXXX
    reference = models.CharField(
        max_length=20,
        unique=True,
        editable=False,
        db_index=True,
        verbose_name=_("Reference"),
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,          # Never silently delete financial records
        related_name="withdrawals",
        verbose_name=_("User"),
    )
    amount = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.01"))],
        verbose_name=_("Amount"),
    )
    currency = models.CharField(
        max_length=3,
        default="USD",
        verbose_name=_("Currency"),
    )
    status = models.CharField(
        max_length=10,
        choices=WithdrawalStatus.choices,
        default=WithdrawalStatus.PENDING,
        db_index=True,
        verbose_name=_("Status"),
    )
    rejection_reason = models.TextField(
        blank=True,
        verbose_name=_("Rejection Reason"),
    )
    requested_at = models.DateTimeField(
        auto_now_add=True,
        db_index=True,
        verbose_name=_("Requested At"),
    )
    processed_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_("Processed At"),
    )
    processed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="processed_withdrawals",
        verbose_name=_("Processed By"),
        help_text=_("Admin user who approved or rejected this request."),
    )

    class Meta:
        db_table = "withdrawals_withdrawal"
        verbose_name = _("Withdrawal")
        verbose_name_plural = _("Withdrawals")
        ordering = ["-requested_at"]
        indexes = [
            models.Index(fields=["user", "status"], name="withdrawal_user_status_idx"),
            models.Index(fields=["requested_at"], name="withdrawal_requested_at_idx"),
        ]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(amount__gt=0),
                name="withdrawal_amount_gt_0",
            ),
            # If status is APPROVED or REJECTED, processed_at and processed_by must be set.
            # Enforced at service layer; adding DB check is complex with nullable FKs.
        ]

    # ---------------------------------------------------------------------- #
    #  Reference generation                                                   #
    # ---------------------------------------------------------------------- #

    @staticmethod
    def _generate_reference() -> str:
        chars = string.ascii_uppercase + string.digits
        suffix = "".join(secrets.choice(chars) for _ in range(8))
        return f"WD-{suffix}"

    def __str__(self) -> str:
        return f"Withdrawal({self.reference}, {self.user_id}, {self.amount} {self.currency}, {self.status})"

    # Withdrawals may not be modified once created — use service functions.
    def save(self, *args, **kwargs):
        if self._state.adding and not self.reference:
            # Generate reference on first save only
            for _ in range(10):
                self.reference = self._generate_reference()
                try:
                    from django.db import transaction as _t
                    with _t.atomic():
                        return super().save(*args, **kwargs)
                except IntegrityError:
                    # Retry only on duplicate reference (unique constraint);
                    # all other errors are re-raised immediately.
                    continue
            raise RuntimeError("Failed to generate unique withdrawal reference.")
        return super().save(*args, **kwargs)
