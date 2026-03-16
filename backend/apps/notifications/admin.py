from django.contrib import admin, messages
from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone
from unfold.admin import ModelAdmin

from .models import Notification

User = get_user_model()


@admin.register(Notification)
class NotificationAdmin(ModelAdmin):
    list_display = (
        "title_display",
        "user_display",
        "is_sent_display",
        "is_read_display",
        "created_at_display",
    )
    list_filter = ("is_read", "created_at")
    search_fields = ("title", "body", "user__phone", "user__first_name", "user__last_name")
    ordering = ("-created_at",)
    exclude = ("channel",)
    readonly_fields = ()

    fieldsets = (
        (
            None,
            {
                "fields": (
                    "title",
                    "body",
                    "user",
                    "play_sound",
                    "vibrate",
                )
            },
        ),
    )

    def get_form(self, request, obj=None, change=False, **kwargs):
        form = super().get_form(request, obj, change, **kwargs)

        if "play_sound" in form.base_fields:
            form.base_fields["play_sound"].label = "Звук"

        if "user" in form.base_fields:
            form.base_fields["user"].empty_label = "Выберите значение"

        return form

    @admin.display(description="Заголовок", ordering="title")
    def title_display(self, obj: Notification):
        return obj.title

    @admin.display(description="Пользователь", ordering="user__phone")
    def user_display(self, obj: Notification):
        if obj.user_id:
            return obj.user
        return "Все пользователи"

    @admin.display(boolean=True, description="Отправлено", ordering="sent_at")
    def is_sent_display(self, obj: Notification):
        return bool(obj.sent_at)

    @admin.display(boolean=True, description="Прочитано", ordering="is_read")
    def is_read_display(self, obj: Notification):
        return obj.is_read

    @admin.display(description="Создано", ordering="created_at")
    def created_at_display(self, obj: Notification):
        return obj.created_at

    def save_model(self, request, obj, form, change):
        obj.channel = Notification.CHANNEL_PUSH

        if change:
            super().save_model(request, obj, form, change)
            return

        send_time = timezone.now()

        if obj.user_id:
            obj.sent_at = send_time
            super().save_model(request, obj, form, change)
            return

        users = list(User.objects.filter(is_active=True).order_by("id"))
        if not users:
            self.message_user(request, "Нет активных пользователей для отправки.", level=messages.WARNING)
            obj.sent_at = send_time
            super().save_model(request, obj, form, change)
            return

        with transaction.atomic():
            first_user = users[0]
            obj.user = first_user
            obj.sent_at = send_time
            super().save_model(request, obj, form, change)

            if len(users) > 1:
                Notification.objects.bulk_create(
                    [
                        Notification(
                            user=user,
                            channel=Notification.CHANNEL_PUSH,
                            title=obj.title,
                            body=obj.body,
                            play_sound=obj.play_sound,
                            vibrate=obj.vibrate,
                            is_read=False,
                            sent_at=send_time,
                        )
                        for user in users[1:]
                    ],
                    batch_size=500,
                )

        self.message_user(
            request,
            f"Push-уведомление отправлено {len(users)} пользователям.",
            level=messages.SUCCESS,
        )
