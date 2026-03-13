from django.contrib import admin
from unfold.admin import ModelAdmin

from .models import Notification

Notification._meta.verbose_name = "Уведомление"
Notification._meta.verbose_name_plural = "Уведомления"


@admin.register(Notification)
class NotificationAdmin(ModelAdmin):
    list_display = (
        "user_display",
        "channel_display",
        "title_display",
        "is_read_display",
        "created_at_display",
        "sent_at_display",
    )
    list_filter = ("channel", "is_read", "created_at")
    search_fields = ("user__phone", "title", "body")
    readonly_fields = ("user", "channel", "title", "body", "sent_at", "created_at")

    @admin.display(description="Пользователь", ordering="user__phone")
    def user_display(self, obj: Notification):
        return obj.user

    @admin.display(description="Канал", ordering="channel")
    def channel_display(self, obj: Notification):
        channel_map = {
            Notification.CHANNEL_PUSH: "Пуш",
            Notification.CHANNEL_SMS: "SMS",
            Notification.CHANNEL_IN_APP: "В приложении",
        }
        return channel_map.get(obj.channel, obj.channel)

    @admin.display(description="Заголовок", ordering="title")
    def title_display(self, obj: Notification):
        return obj.title

    @admin.display(boolean=True, description="Прочитано", ordering="is_read")
    def is_read_display(self, obj: Notification):
        return obj.is_read

    @admin.display(description="Создано", ordering="created_at")
    def created_at_display(self, obj: Notification):
        return obj.created_at

    @admin.display(description="Отправлено", ordering="sent_at")
    def sent_at_display(self, obj: Notification):
        return obj.sent_at

    def has_add_permission(self, request) -> bool:
        return False
