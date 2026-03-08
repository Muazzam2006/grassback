"""
Celery tasks for the reservations app.

expire_stale_reservations runs every 5 minutes via Celery Beat.
It performs a single bulk UPDATE — no per-row locks, no Python-side loops.
"""
from celery import shared_task
from celery.utils.log import get_task_logger

logger = get_task_logger(__name__)


@shared_task(
    name="reservations.expire_stale",
    max_retries=3,
    default_retry_delay=30,
    acks_late=True,
)
def expire_stale_reservations_task() -> int:
    """
    Expire all ACTIVE reservations whose expires_at has passed.

    Runs every 5 minutes (configured in CELERY_BEAT_SCHEDULE).
    Returns the number of reservations marked EXPIRED.
    """
    from .services import expire_stale_reservations  # local import to avoid circular

    count = expire_stale_reservations()
    if count:
        logger.info("Expired %d stale reservation(s).", count)
    return count
