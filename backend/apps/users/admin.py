from django import forms
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.forms import ReadOnlyPasswordHashField
from django.db.models import QuerySet
from django.utils.translation import gettext_lazy as _

from .models import OTPToken, User, UserStatusHistory


class CustomUserCreationForm(forms.ModelForm):
    password1 = forms.CharField(label=_("Password"), widget=forms.PasswordInput)
    password2 = forms.CharField(
        label=_("Password confirmation"), widget=forms.PasswordInput
    )

    class Meta:
        model = User
        fields = ("phone", "first_name", "last_name", "parent", "status")

    def clean_password2(self):
        password1 = self.cleaned_data.get("password1")
        password2 = self.cleaned_data.get("password2")

        if not password1 or not password2:
            raise forms.ValidationError("Password is required.")

        if password1 != password2:
            raise forms.ValidationError("Passwords do not match.")

        return password2

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password1"])
        if commit:
            user.save()
        return user


class CustomUserChangeForm(forms.ModelForm):
    password = ReadOnlyPasswordHashField(
        label=_("Password"),
        help_text=_("Raw password hashes are stored in the database. Use the form above to change the password."),
    )

    class Meta:
        model = User
        fields = "__all__"


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    form = CustomUserChangeForm
    add_form = CustomUserCreationForm
    model = User

    list_display = (
        "id",
        "phone",
        "first_name",
        "last_name",
        "status",
        "parent",     
        "level",   
        "bonus_balance",
        "is_active",
        "is_staff",
        "date_joined",
    )
    list_filter = (
        "status",
        "level",
        "is_active",
        "is_staff",
        "date_joined",
    )
    search_fields = (
        "phone",
        "first_name",
        "last_name",
        "referral_code",
    )
    readonly_fields = (
        "date_joined",
        "last_login",
        "referral_code",
        "personal_turnover",
        "team_turnover",
        "bonus_balance",
        # MPTT internal fields — never edit manually
        "lft",
        "rght",
        "tree_id",
        "level",
    )
    ordering = ("-date_joined",)

    list_select_related = ("parent",)

    autocomplete_fields = ("parent",)

    actions = None

    fieldsets = (
        (None, {"fields": ("phone", "password")}),
        (_("Personal Info"), {"fields": ("first_name", "last_name")}),
        (
            _("MLM Info"),
            {
                "fields": (
                    "status",
                    "parent",      
                    "referral_code",
                )
            },
        ),
        (
            _("Financials"),
            {
                "fields": (
                    "personal_turnover",
                    "team_turnover",
                    "bonus_balance",
                )
            },
        ),
        (
            _("Permissions"),
            {
                "fields": (
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                ),
            },
        ),
        (_("Important dates"), {"fields": ("last_login", "date_joined")}),
        (
            _("MPTT tree fields (read-only)"),
            {
                "classes": ("collapse",),
                "fields": ("lft", "rght", "tree_id", "level"),
            },
        ),
    )

    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": (
                    "phone",
                    "first_name",
                    "last_name",
                    "parent",  
                    "status",
                    "password1",
                    "password2",
                ),
            },
        ),
    )

    def get_queryset(self, request) -> QuerySet:
        return (
            super().get_queryset(request)
            .select_related("parent")
        )

    def get_readonly_fields(self, request, obj=None):
        readonly = list(self.readonly_fields)
        if obj:
            readonly.append("parent")
        return readonly



@admin.register(OTPToken)
class OTPTokenAdmin(admin.ModelAdmin):
    """Read-only admin: exposes OTP audit data without revealing raw codes."""

    list_display = ("id", "phone", "purpose", "is_used", "attempts", "expires_at", "created_at")
    list_filter = ("purpose", "is_used")
    search_fields = ("phone",)
    ordering = ("-created_at",)
    readonly_fields = ("id", "phone", "code_hash", "purpose", "is_used", "attempts", "expires_at", "created_at")

    def has_add_permission(self, request) -> bool:
        return False

    def has_change_permission(self, request, obj=None) -> bool:
        return False

    def has_delete_permission(self, request, obj=None) -> bool:
        return False


@admin.register(UserStatusHistory)
class UserStatusHistoryAdmin(admin.ModelAdmin):
    """Read-only view of every MLM status change."""

    list_display = ("user", "old_status", "new_status", "changed_by", "changed_at")
    list_filter = ("old_status", "new_status")
    search_fields = ("user__phone", "user__first_name", "user__last_name")
    ordering = ("-changed_at",)
    readonly_fields = ("user", "old_status", "new_status", "changed_by", "reason", "changed_at")
    list_select_related = ("user", "changed_by")

    def has_add_permission(self, request) -> bool:
        return False

    def has_change_permission(self, request, obj=None) -> bool:
        return False

    def has_delete_permission(self, request, obj=None) -> bool:
        return False