from django.db import models


class Notification(models.Model):

    CHANNEL_PUSH = "push"
    CHANNEL_SMS = "sms"
    CHANNEL_IN_APP = "in_app"
    CHANNEL_CHOICES = [
        (CHANNEL_PUSH, "Push"),
        (CHANNEL_SMS, "SMS"),
        (CHANNEL_IN_APP, "In-App"),
    ]

    user = models.ForeignKey(
        "users.User",
        on_delete=models.CASCADE,
        related_name="notifications",
        verbose_name="Пользователь",
        null=True,
        blank=True,
        help_text="Оставьте пустым, чтобы отправить всем пользователям.",
    )
    channel = models.CharField(max_length=20, choices=CHANNEL_CHOICES, default=CHANNEL_PUSH)
    title = models.CharField(max_length=255, verbose_name="Заголовок")
    body = models.TextField(verbose_name="Сообщение")
    play_sound = models.BooleanField(default=True, verbose_name="Звук")
    vibrate = models.BooleanField(default=True, verbose_name="Вибрация")
    is_read = models.BooleanField(default=False, db_index=True, verbose_name="Прочитано")
    sent_at = models.DateTimeField(null=True, blank=True, verbose_name="Отправлено")
    created_at = models.DateTimeField(auto_now_add=True, db_index=True, verbose_name="Создано")

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Push-уведомление"
        verbose_name_plural = "Push-уведомления"
        indexes = [
            models.Index(fields=["user", "is_read"], name="notif_user_unread_idx"),
        ]

    def __str__(self) -> str:
        recipient = self.user.phone if self.user_id else "Все пользователи"
        return f"[{self.channel}] {self.title} -> {recipient}"
