from django.db import transaction
from django.utils import timezone

from apps.orders.models import Order

from .models import Courier, DeliveryStatus, OrderDelivery

_ALLOWED_TRANSITIONS: dict[str, set[str]] = {
    DeliveryStatus.PENDING:   {DeliveryStatus.SHIPPED, DeliveryStatus.CANCELLED},
    DeliveryStatus.SHIPPED:   {DeliveryStatus.DELIVERED, DeliveryStatus.CANCELLED},
    DeliveryStatus.DELIVERED: set(),
    DeliveryStatus.CANCELLED: set(),
}


class DeliveryError(Exception):
    """Base exception for delivery domain errors."""


class InvalidTransitionError(DeliveryError):
    """Raised when a status transition is not allowed."""


@transaction.atomic
def create_order_delivery(
    order: Order,
    delivery_fee=None,
    courier: Courier | None = None,
    notes: str = "",
) -> OrderDelivery:
    order = (
        Order.objects
        .select_for_update()
        .select_related("delivery_address")
        .get(pk=order.pk)
    )

    if order.delivery_address_id is None:
        raise DeliveryError(
            f"Order {order.pk} has no delivery address — cannot create delivery."
        )

    if OrderDelivery.objects.filter(order=order).exists():
        raise DeliveryError(
            f"A delivery record already exists for order {order.pk}."
        )

    fee = delivery_fee if delivery_fee is not None else order.delivery_fee

    delivery = OrderDelivery.objects.create(
        order=order,
        delivery_address=order.delivery_address,
        courier=courier,
        delivery_fee=fee,
        notes=notes,
    )
                                                                   
    Order.objects.filter(pk=order.pk).update(delivery_fee=fee)

    return delivery


@transaction.atomic
def update_delivery_status(
    delivery: OrderDelivery,
    new_status: str,
    courier: Courier | None = None,
    tracking_number: str | None = None,
    notes: str = "",
) -> OrderDelivery:
    
    delivery = OrderDelivery.objects.select_for_update().get(pk=delivery.pk)
    allowed = _ALLOWED_TRANSITIONS.get(delivery.status, set())

    if new_status not in allowed:
        raise InvalidTransitionError(
            f"Cannot transition from {delivery.status!r} to {new_status!r}. "
            f"Allowed: {allowed or 'none (terminal state)'}."
        )

    update_fields = ["status", "updated_at"]
    delivery.status = new_status

    if new_status == DeliveryStatus.SHIPPED:
        delivery.shipped_at = timezone.now()
        update_fields.append("shipped_at")
        if tracking_number:
            delivery.tracking_number = tracking_number
            update_fields.append("tracking_number")
        if courier:
            delivery.courier = courier
            update_fields.append("courier")

    if new_status == DeliveryStatus.DELIVERED:
        delivery.delivered_at = timezone.now()
        update_fields.append("delivered_at")

    if notes:
        delivery.notes = notes
        update_fields.append("notes")

    delivery.save(update_fields=update_fields)
    return delivery


@transaction.atomic
def assign_courier(delivery: OrderDelivery, courier: Courier) -> OrderDelivery:
    delivery = OrderDelivery.objects.select_for_update().get(pk=delivery.pk)

    if delivery.status not in {DeliveryStatus.PENDING, DeliveryStatus.SHIPPED}:
        raise InvalidTransitionError(
            f"Cannot assign courier to a {delivery.status!r} delivery."
        )

    delivery.courier = courier
    delivery.save(update_fields=["courier", "updated_at"])
    return delivery
