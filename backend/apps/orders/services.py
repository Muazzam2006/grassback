from django.db import transaction
from django.db.models import F
from django.contrib.auth import get_user_model

from apps.products.models import ProductVariant

from .models import Order, OrderItem, OrderLifecycleLog, OrderStatus

User = get_user_model()


class OrderTransitionError(Exception):
    """Raised when an order cannot be transitioned to the requested status."""

                                                   
_ALLOWED_TRANSITIONS: dict[str, set[str]] = {
    OrderStatus.CREATED:   {OrderStatus.RESERVED, OrderStatus.CANCELLED},
    OrderStatus.RESERVED:  {OrderStatus.CONFIRMED, OrderStatus.CANCELLED},
    OrderStatus.CONFIRMED: {OrderStatus.SHIPPED, OrderStatus.CANCELLED},
    OrderStatus.SHIPPED:   {OrderStatus.DELIVERED, OrderStatus.CANCELLED},
    OrderStatus.DELIVERED: set(),                         
    OrderStatus.CANCELLED: set(),                         
}


@transaction.atomic
def transition_order_status(
    order: Order,
    new_status: str,
    changed_by: User | None = None,
    note: str = "",
) -> Order:
    order = Order.objects.select_for_update().get(pk=order.pk)

    allowed = _ALLOWED_TRANSITIONS.get(order.status, set())
    if new_status not in allowed:
        raise OrderTransitionError(
            f"Cannot transition order from {order.status!r} to {new_status!r}. "
            f"Allowed: {sorted(allowed) or 'none (terminal)'}."
        )

    old_status = order.status
    order.status = new_status
    order.save(update_fields=["status", "updated_at"])

    OrderLifecycleLog.objects.create(
        order=order,
        from_status=old_status,
        to_status=new_status,
        changed_by=changed_by,
        note=note,
    )
    return order


@transaction.atomic
def confirm_order(
    order: Order,
    admin_user: User | None = None,
    note: str = "",
) -> Order:
    log_note = note or "Order confirmed by admin."
    return transition_order_status(
        order, OrderStatus.CONFIRMED, changed_by=admin_user,
        note=log_note,
    )


@transaction.atomic
def ship_order(
    order: Order,
    admin_user: User | None = None,
    tracking_number: str = "",
    note: str = "",
) -> Order:
    base_note = f"Shipped. Tracking: {tracking_number or '—'}"
    log_note = f"{base_note}. {note}" if note else base_note
    order = transition_order_status(
        order, OrderStatus.SHIPPED, changed_by=admin_user,
        note=log_note,
    )
    return order


@transaction.atomic
def deliver_order(
    order: Order,
    admin_user: User | None = None,
    note: str = "",
) -> Order:
    log_note = note or "Delivered to customer (COD)."
    return transition_order_status(
        order, OrderStatus.DELIVERED, changed_by=admin_user,
        note=log_note,
    )


@transaction.atomic
def cancel_order(
    order: Order,
    changed_by: User | None = None,
    note: str = "Cancelled.",
) -> Order:
    order = Order.objects.select_for_update().get(pk=order.pk)

    if order.status in (OrderStatus.DELIVERED, OrderStatus.CANCELLED):
        raise OrderTransitionError(
            f"Order with status {order.status!r} cannot be cancelled."
        )

                                                                      
    items_with_variant = OrderItem.objects.filter(
        order=order,
        variant__isnull=False,
    ).values("variant_id", "quantity")

    for row in items_with_variant:
        ProductVariant.objects.filter(pk=row["variant_id"]).update(
            stock=F("stock") + row["quantity"]
        )

    old_status = order.status
    order.status = OrderStatus.CANCELLED
    order.save(update_fields=["status", "updated_at"])

    OrderLifecycleLog.objects.create(
        order=order,
        from_status=old_status,
        to_status=OrderStatus.CANCELLED,
        changed_by=changed_by,
        note=note,
    )
    return order
