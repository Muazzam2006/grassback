import logging

from django.db.models.signals import post_save
from django.dispatch import receiver

from apps.orders.models import Order, OrderStatus

logger = logging.getLogger(__name__)


@receiver(post_save, sender=Order)
def on_order_delivered(sender, instance: Order, created: bool, update_fields=None, **kwargs) -> None:
    if instance.status != OrderStatus.DELIVERED:
        return

    if (not created) and update_fields is not None and "status" not in update_fields:
        return

    try:
        from apps.bonuses.tasks import distribute_and_confirm_bonuses_task

        distribute_and_confirm_bonuses_task.delay(str(instance.pk))
    except Exception:
        logger.exception("Failed to dispatch bonus task for delivered order %s", instance.pk)
