from decimal import Decimal

from django.db import models

class NetworkStats(models.Model):
    user = models.OneToOneField(
        "users.User",
        on_delete=models.CASCADE,
        related_name="network_stats",
        verbose_name="User",
    )
    team_size = models.PositiveIntegerField(default=0, verbose_name="Team Size")
    team_sales = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=Decimal("0.00"),
        verbose_name="Team Sales",
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "mlm_networkstats"
        verbose_name = "Network Stats"
        verbose_name_plural = "Network Stats"

    def __str__(self) -> str:
        return f"NetworkStats({self.user.phone})"


class StatusThreshold(models.Model):

    STATUS_CHOICES = [
        ("BRONZE", "Bronze"),
        ("SILVER", "Silver"),
        ("GOLD", "Gold"),
    ]

    status = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES,
        unique=True,
        db_index=True,
        verbose_name="Status",
    )
    min_personal_turnover = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=Decimal("0.00"),
        verbose_name="Min Personal Turnover",
        help_text="Minimum cumulative personal sales to reach this status.",
    )
    min_team_turnover = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=Decimal("0.00"),
        verbose_name="Min Team Turnover",
        help_text="Minimum cumulative downline sales to reach this status.",
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "mlm_status_threshold"
        verbose_name = "Status Threshold"
        verbose_name_plural = "Status Thresholds"
        ordering = ["min_personal_turnover"]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(min_personal_turnover__gte=0),
                name="threshold_personal_gte_0",
            ),
            models.CheckConstraint(
                condition=models.Q(min_team_turnover__gte=0),
                name="threshold_team_gte_0",
            ),
        ]

    def __str__(self) -> str:
        return (
            f"StatusThreshold({self.status}: "
            f"personal≥{self.min_personal_turnover}, "
            f"team≥{self.min_team_turnover})"
        )
