from django.contrib.auth import get_user_model
from django.db import transaction

from .models import StatusThreshold

User = get_user_model()
                                                                            
_STATUS_ORDER = ["BRONZE", "SILVER", "GOLD"]


@transaction.atomic
def promote_user_status(user: User) -> bool:
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
            continue
        if (
            user.personal_turnover >= threshold.min_personal_turnover
            and user.team_turnover >= threshold.min_team_turnover
        ):
            best_status = status
                                                                            
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
