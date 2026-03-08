"""
MLM domain service layer.

`promote_user_status` is the canonical function that determines a user's
correct status from DB-configured thresholds — no hardcoded constants.
"""
from django.contrib.auth import get_user_model
from django.db import transaction

from .models import StatusThreshold

User = get_user_model()

# Ordered from lowest to highest so we iterate upward and find the best match.
_STATUS_ORDER = ["BRONZE", "SILVER", "GOLD"]


@transaction.atomic
def promote_user_status(user: User) -> bool:
    """
    Evaluate the highest status the user qualifies for and update if changed.

    Algorithm
    ---------
    1. Load all active thresholds from DB in ascending order.
    2. Walk them from lowest to highest.
    3. Keep track of the highest threshold the user satisfies.
    4. If the resolved status differs from `user.status`, UPDATE it.

    Returns True if the status was promoted, False if unchanged.

    Called after bonus confirmation so that turnover counters are already
    up-to-date on the locked user row.
    """
    thresholds = {
        t.status: t
        for t in StatusThreshold.objects.select_for_update().filter(
            status__in=_STATUS_ORDER
        )
    }

    best_status = "NEW"
    for status in _STATUS_ORDER:
        threshold = thresholds.get(status)
        if threshold is None:
            # No rule configured for this level — skip but do not break,
            # allowing a gap in configuration (e.g. only BRONZE + GOLD defined).
            continue
        if (
            user.personal_turnover >= threshold.min_personal_turnover
            and user.team_turnover >= threshold.min_team_turnover
        ):
            best_status = status
        # Do NOT break on failure: a user can satisfy BRONZE but not SILVER,
        # yet still satisfy GOLD if thresholds are non-monotonic in config.

    if user.status != best_status:
        from apps.users.models import UserStatusHistory

        old_status = user.status
        User.objects.filter(pk=user.pk).update(status=best_status)
        user.status = best_status

        UserStatusHistory.objects.create(
            user_id=user.pk,
            old_status=old_status,
            new_status=best_status,
            changed_by=None,
            reason="Automatic promotion based on turnover thresholds.",
        )
        return True

    return False
