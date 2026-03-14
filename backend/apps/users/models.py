import hashlib
import secrets
import string
import uuid
from decimal import Decimal

from django.contrib.auth.base_user import AbstractBaseUser
from django.contrib.auth.models import PermissionsMixin
from django.core.exceptions import ValidationError
from django.db import IntegrityError, models, transaction
from django.db.models import Q
from django.utils import timezone
from mptt.fields import TreeForeignKey
from mptt.models import MPTTModel

from .managers import UserManager


class UserStatus(models.TextChoices):
    NEW = "NEW", "New"
    BRONZE = "BRONZE", "Bronze"
    SILVER = "SILVER", "Silver"
    GOLD = "GOLD", "Gold"


class User(MPTTModel, AbstractBaseUser, PermissionsMixin):
    
    phone = models.CharField(
        max_length=20,
        unique=True,
        db_index=True,
        verbose_name="Телефон",
    )
    first_name = models.CharField(max_length=150, verbose_name="Имя")
    last_name = models.CharField(max_length=150, verbose_name="Фамилия")
    address = models.CharField(max_length=255, blank=True, default="", verbose_name="Адрес")
    is_active = models.BooleanField(
        default=True,
        verbose_name="Активен",
        help_text="Определяет, должен ли этот пользователь считаться активным.",
    )
    is_staff = models.BooleanField(
        default=False,
        verbose_name="Статус персонала",
        help_text="Определяет, может ли пользователь входить в панель администратора.",
    )
    date_joined = models.DateTimeField(
        default=timezone.now,
        verbose_name="Дата регистрации",
    )

    referral_code = models.CharField(
        max_length=8,
        unique=True,
        db_index=True,
        editable=False,
        verbose_name="Реферальный код",
        help_text="Уникальный реферальный код агента",
    )

    parent = TreeForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="children",
        db_index=True,
        verbose_name="Спонсор",
        help_text="Агент, пригласивший пользователя (узел MPTT)",
    )

    status = models.CharField(
        max_length=10,
        choices=UserStatus.choices,
        default=UserStatus.NEW,
        db_index=True,
        verbose_name="Статус",
    )

    personal_turnover = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=Decimal("0.00"),
        verbose_name="Личный оборот",
    )
    team_turnover = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=Decimal("0.00"),
        verbose_name="Командный оборот",
    )
    bonus_balance = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=Decimal("0.00"),
        verbose_name="Бонусный баланс",
    )

    objects = UserManager()

    USERNAME_FIELD = "phone"
    REQUIRED_FIELDS = ["first_name", "last_name"]

    class MPTTMeta:
        parent_attr = "parent"
        order_insertion_by = ["date_joined"]

    class Meta:
        verbose_name = "User"
        verbose_name_plural = "Users"
        db_table = "users_user"
        indexes = [
            models.Index(
                fields=["tree_id", "lft", "rght"],
                name="users_user_tree_range_idx",
            ),
            models.Index(fields=["level"], name="users_user_level_idx"),
            models.Index(fields=["status"], name="users_user_status_idx"),
            models.Index(fields=["-date_joined"], name="users_user_date_joined_idx"),
        ]
        constraints = [
            models.CheckConstraint(
                condition=Q(personal_turnover__gte=0),
                name="users_personal_turnover_gte_0",
            ),
            models.CheckConstraint(
                condition=Q(team_turnover__gte=0),
                name="users_team_turnover_gte_0",
            ),
            models.CheckConstraint(
                condition=Q(bonus_balance__gte=0),
                name="users_bonus_balance_gte_0",
            ),
            models.CheckConstraint(
                condition=Q(parent__isnull=True) | ~Q(parent=models.F("pk")),
                name="users_not_self_sponsored",
            ),
        ]

    @property
    def sponsor(self) -> "User | None":
        return self.parent

    @property
    def sponsor_id(self) -> int | None:
        return self.parent_id

    def clean(self) -> None:
        super().clean()
        if self.parent_id and self.parent_id == self.pk:
            raise ValidationError({"parent": "User cannot be their own sponsor."})
        if self.pk and self.parent_id:
            try:
                parent_obj = User.objects.get(pk=self.parent_id)
                if parent_obj.is_descendant_of(self):
                    raise ValidationError(
                        {"parent": "Chosen sponsor is a descendant of this user — this would create a cycle."}
                    )
            except User.DoesNotExist:
                pass

    def __str__(self) -> str:
        return f"{self.first_name} {self.last_name} ({self.phone})"

    def get_full_name(self) -> str:
        return f"{self.first_name} {self.last_name}".strip()

    def get_short_name(self) -> str:
        return self.first_name


    @staticmethod
    def _generate_referral_code() -> str:
        alphabet = string.ascii_uppercase + string.digits
        return "".join(secrets.choice(alphabet) for _ in range(8))

    def save(self, *args, **kwargs) -> None: 
        if not self.referral_code:
            for _ in range(10):
                self.referral_code = self._generate_referral_code()
                try:
                    with transaction.atomic():
                        return super().save(*args, **kwargs)
                except IntegrityError:
                    continue
            raise RuntimeError("Failed to generate unique referral code after 10 attempts.")
        return super().save(*args, **kwargs)



class OTPPurpose(models.TextChoices):
    REGISTER = "REGISTER", "Registration"
    LOGIN = "LOGIN", "Login"
    RESET = "RESET", "Password Reset"


class OTPToken(models.Model):
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    phone = models.CharField(max_length=20, db_index=True)
    code_hash = models.CharField(max_length=64, verbose_name="Code Hash (SHA-256)")
    purpose = models.CharField(
        max_length=10,
        choices=OTPPurpose.choices,
        default=OTPPurpose.REGISTER,
        db_index=True,
    )
    is_used = models.BooleanField(default=False, db_index=True)
    attempts = models.PositiveIntegerField(default=0)
    expires_at = models.DateTimeField(db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "users_otp_token"
        verbose_name = "OTP Token"
        verbose_name_plural = "OTP Tokens"
        ordering = ["-created_at"]
        indexes = [
            models.Index(
                fields=["phone", "purpose", "is_used", "expires_at"],
                name="otp_phone_purpose_idx",
            ),
        ]

    def __str__(self) -> str:
        return f"OTPToken({self.phone}, {self.purpose}, used={self.is_used})"

    @staticmethod
    def hash_code(raw_code: str) -> str:
        return hashlib.sha256(raw_code.encode()).hexdigest()

    def verify(self, raw_code: str) -> bool:
        return self.code_hash == self.hash_code(raw_code)



class UserStatusHistory(models.Model):
    
    user = models.ForeignKey(
        "users.User",
        on_delete=models.PROTECT,
        related_name="status_history",
    )
    old_status = models.CharField(max_length=10, choices=UserStatus.choices)
    new_status = models.CharField(max_length=10, choices=UserStatus.choices)
    changed_by = models.ForeignKey(
        "users.User",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="status_changes_made",
    )
    reason = models.TextField(blank=True)
    changed_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        db_table = "users_status_history"
        verbose_name = "User Status History"
        verbose_name_plural = "User Status History"
        ordering = ["-changed_at"]
        indexes = [
            models.Index(fields=["user", "changed_at"], name="status_history_user_idx"),
        ]

    def __str__(self) -> str:
        return (
            f"StatusHistory({self.user_id}: "
            f"{self.old_status}→{self.new_status} @ {self.changed_at})"
        )
