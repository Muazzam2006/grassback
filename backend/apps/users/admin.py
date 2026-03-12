from django import forms
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.forms import ReadOnlyPasswordHashField
from django.db.models import QuerySet
from django.utils.translation import gettext_lazy as _

from .models import User, UserStatusHistory

User._meta.verbose_name = "Пользователь"
User._meta.verbose_name_plural = "Пользователи"
UserStatusHistory._meta.verbose_name = "История статусов"
UserStatusHistory._meta.verbose_name_plural = "История статусов"


class CustomUserCreationForm(forms.ModelForm):
    password1 = forms.CharField(label=_("Пароль"), widget=forms.PasswordInput)
    password2 = forms.CharField(
        label=_("Подтверждение пароля"), widget=forms.PasswordInput
    )

    class Meta:
        model = User
        fields = ("phone", "first_name", "last_name", "address", "parent", "status")

    def clean_password2(self):
        password1 = self.cleaned_data.get("password1")
        password2 = self.cleaned_data.get("password2")

        if not password1 or not password2:
            raise forms.ValidationError("Пароль обязателен.")

        if password1 != password2:
            raise forms.ValidationError("Пароли не совпадают.")

        return password2

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password1"])
        if commit:
            user.save()
        return user


class CustomUserChangeForm(forms.ModelForm):
    password = ReadOnlyPasswordHashField(
        label=_("Пароль"),
        help_text=_("В базе хранится хеш пароля. Чтобы изменить пароль, используйте форму выше."),
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
        "phone_display",
        "first_name_display",
        "last_name_display",
        "address_display",
        "status_display",
        "sponsor_display",
        "bonus_balance_display",
        "is_active_display",
        "is_staff_display",
        "date_joined_display",
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
    )
    ordering = ("-date_joined",)

    list_select_related = ("parent",)

    autocomplete_fields = ("parent",)

    actions = None

    fieldsets = (
        (None, {"fields": ("phone", "password")}),
        (_("Личные данные"), {"fields": ("first_name", "last_name", "address")}),
        (
            _("MLM-данные"),
            {
                "fields": (
                    "status",
                    "parent",
                    "referral_code",
                )
            },
        ),
        (
            _("Финансы"),
            {
                "fields": (
                    "personal_turnover",
                    "team_turnover",
                    "bonus_balance",
                )
            },
        ),
        (
            _("Права доступа"),
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
        (_("Важные даты"), {"fields": ("last_login", "date_joined")}),
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
                    "address",
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

    @admin.display(description="Телефон", ordering="phone")
    def phone_display(self, obj: User):
        return obj.phone

    @admin.display(description="Имя", ordering="first_name")
    def first_name_display(self, obj: User):
        return obj.first_name

    @admin.display(description="Фамилия", ordering="last_name")
    def last_name_display(self, obj: User):
        return obj.last_name

    @admin.display(description="Адрес", ordering="address")
    def address_display(self, obj: User):
        return obj.address

    @admin.display(description="Статус", ordering="status")
    def status_display(self, obj: User):
        status_map = {
            "NEW": "Новый",
            "BRONZE": "Бронза",
            "SILVER": "Серебро",
            "GOLD": "Золото",
        }
        return status_map.get(obj.status, obj.status)

    @admin.display(description="Спонсор", ordering="parent")
    def sponsor_display(self, obj: User):
        return obj.parent

    @admin.display(description="Бонусный баланс", ordering="bonus_balance")
    def bonus_balance_display(self, obj: User):
        return obj.bonus_balance

    @admin.display(boolean=True, description="Активен", ordering="is_active")
    def is_active_display(self, obj: User):
        return obj.is_active

    @admin.display(boolean=True, description="Сотрудник", ordering="is_staff")
    def is_staff_display(self, obj: User):
        return obj.is_staff

    @admin.display(description="Дата регистрации", ordering="date_joined")
    def date_joined_display(self, obj: User):
        return obj.date_joined

    def get_readonly_fields(self, request, obj=None):
        readonly = list(self.readonly_fields)
        if obj:
            readonly.append("parent")
        return readonly



@admin.register(UserStatusHistory)
class UserStatusHistoryAdmin(admin.ModelAdmin):

    list_display = (
        "user_display",
        "old_status_display",
        "new_status_display",
        "changed_by_display",
        "changed_at_display",
    )
    list_filter = ("old_status", "new_status")
    search_fields = ("user__phone", "user__first_name", "user__last_name")
    ordering = ("-changed_at",)
    readonly_fields = ("user", "old_status", "new_status", "changed_by", "reason", "changed_at")
    list_select_related = ("user", "changed_by")

    @admin.display(description="Пользователь", ordering="user__phone")
    def user_display(self, obj: UserStatusHistory):
        return obj.user

    @admin.display(description="Старый статус", ordering="old_status")
    def old_status_display(self, obj: UserStatusHistory):
        status_map = {
            "NEW": "Новый",
            "BRONZE": "Бронза",
            "SILVER": "Серебро",
            "GOLD": "Золото",
        }
        return status_map.get(obj.old_status, obj.old_status)

    @admin.display(description="Новый статус", ordering="new_status")
    def new_status_display(self, obj: UserStatusHistory):
        status_map = {
            "NEW": "Новый",
            "BRONZE": "Бронза",
            "SILVER": "Серебро",
            "GOLD": "Золото",
        }
        return status_map.get(obj.new_status, obj.new_status)

    @admin.display(description="Кто изменил", ordering="changed_by")
    def changed_by_display(self, obj: UserStatusHistory):
        return obj.changed_by

    @admin.display(description="Дата изменения", ordering="changed_at")
    def changed_at_display(self, obj: UserStatusHistory):
        return obj.changed_at

    def has_add_permission(self, request) -> bool:
        return False

    def has_change_permission(self, request, obj=None) -> bool:
        return False

    def has_delete_permission(self, request, obj=None) -> bool:
        return False

    def get_model_perms(self, request):
        if request.user.is_superuser:
            return super().get_model_perms(request)
        return {}
