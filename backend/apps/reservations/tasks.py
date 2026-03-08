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
    from .services import expire_stale_reservations                                  

    count = expire_stale_reservations()
    if count:
        logger.info("Expired %d stale reservation(s).", count)
    return count
