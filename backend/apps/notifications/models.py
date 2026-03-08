"""
Notifications app models.

This app manages notification delivery (push, SMS, in-app) to users.
Domain statistics (e.g. NetworkStats) have been moved to apps.mlm where
they belong architecturally (A-4).
"""
from django.db import models


class Notification(models.Model):
    """Placeholder model for future notification delivery records."""

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
        verbose_name="Recipient",
    )
    channel = models.CharField(max_length=20, choices=CHANNEL_CHOICES, default=CHANNEL_IN_APP)
    title = models.CharField(max_length=255)
    body = models.TextField()
    is_read = models.BooleanField(default=False, db_index=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Notification"
        verbose_name_plural = "Notifications"
        indexes = [
            models.Index(fields=["user", "is_read"], name="notif_user_unread_idx"),
        ]

    def __str__(self) -> str:
        return f"[{self.channel}] {self.title} → {self.user.phone}"