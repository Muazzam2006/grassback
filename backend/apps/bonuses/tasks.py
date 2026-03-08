from celery import shared_task
from celery.utils.log import get_task_logger

logger = get_task_logger(__name__)


@shared_task(
    name="bonuses.distribute_and_confirm",
    max_retries=5,
    default_retry_delay=60,
    acks_late=True,
)
def distribute_and_confirm_bonuses_task(order_id: str) -> dict:
    from apps.orders.models import Order
    from .services import distribute_order_bonuses, confirm_order_bonuses

    try:
        order = Order.objects.get(pk=order_id)
    except Order.DoesNotExist:
        logger.error("distribute_and_confirm_bonuses_task: order %s not found.", order_id)
        return {"distributed": 0, "confirmed": 0}

    try:
        created = distribute_order_bonuses(order)
        confirmed_count = confirm_order_bonuses(order)
        logger.info(
            "Bonuses for order %s: distributed=%d, confirmed=%d",
            order_id, len(created), confirmed_count,
        )
        return {"distributed": len(created), "confirmed": confirmed_count}
    except Exception as exc:
        logger.exception(
            "Bonus distribution failed for order %s — will retry.", order_id
        )
        raise distribute_and_confirm_bonuses_task.retry(exc=exc)
