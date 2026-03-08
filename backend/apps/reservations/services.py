from decimal import Decimal

from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models import F, Sum
from django.utils import timezone

from apps.products.models import ProductVariant
from apps.orders.models import Order, OrderItem, OrderStatus
from apps.delivery.models import DeliveryAddress

from .models import Reservation, ReservationStatus

User = get_user_model()


_TIMEOUT_MINUTES: int = getattr(settings, "RESERVATION_TIMEOUT_MINUTES", 21600)           
_MAX_DISTINCT_PRODUCTS_PER_USER = 3


class ReservationError(Exception):
    """Base class for all reservation-domain errors."""


class InsufficientStockError(ReservationError):
    """Raised when available stock is less than requested quantity."""


class DuplicateActiveReservationError(ReservationError):
    """Raised when user already has an ACTIVE reservation for the same variant."""


class ProductLimitExceededError(ReservationError):
    """Raised when user already has reservations on 3 distinct products."""


class ReservationNotActiveError(ReservationError):
    """Raised when a reservation is not in ACTIVE status."""


class ReservationExpiredError(ReservationError):
    """Raised when a reservation has passed its expires_at timestamp."""


class ReservationConversionError(ReservationError):
    """Raised when checkout cannot convert reservations (stock or status mismatch)."""


@transaction.atomic
def reserve_variant(
    user: User,
    variant: ProductVariant,
    quantity: int,
) -> Reservation:
                                     
    if quantity < 1:
        raise ValueError("Quantity must be at least 1.")

                                                                                 
    locked_variant = (
        ProductVariant.objects
        .select_for_update()
        .get(pk=variant.pk)
    )

                                        
    active_reserved = (
        Reservation.objects
        .filter(variant=locked_variant, status=ReservationStatus.ACTIVE)
        .aggregate(total=Sum("quantity"))["total"]
    ) or 0

    available = locked_variant.stock - active_reserved

                                                   
    if Reservation.objects.filter(
        user=user,
        variant=locked_variant,
        status=ReservationStatus.ACTIVE,
    ).exists():
        raise DuplicateActiveReservationError(
            "You already have an active reservation for this variant. "
            "Cancel or convert it before creating a new one."
        )

                                       
    active_product_count = (
        Reservation.objects
        .filter(user=user, status=ReservationStatus.ACTIVE)
        .values("variant__product_id")
        .distinct()
        .count()
    )
                                                                           
    current_product_ids = set(
        Reservation.objects
        .filter(user=user, status=ReservationStatus.ACTIVE)
        .values_list("variant__product_id", flat=True)
    )
    if (
        locked_variant.product_id not in current_product_ids
        and active_product_count >= _MAX_DISTINCT_PRODUCTS_PER_USER
    ):
        raise ProductLimitExceededError(
            f"You can have at most {_MAX_DISTINCT_PRODUCTS_PER_USER} distinct "
            "products in active reservations."
        )

                            
    if available < quantity:
        raise InsufficientStockError(
            f"Only {available} units available for this variant "
            f"(requested {quantity})."
        )

                                   
    now = timezone.now()
    expires_at = now + timezone.timedelta(minutes=_TIMEOUT_MINUTES)

    reservation = Reservation.objects.create(
        user=user,
        variant=locked_variant,
        quantity=quantity,
        status=ReservationStatus.ACTIVE,
        expires_at=expires_at,
    )
    return reservation


@transaction.atomic
def cancel_reservation(reservation: Reservation) -> Reservation:
    reservation = (
        Reservation.objects
        .select_for_update()
        .get(pk=reservation.pk)
    )

    if reservation.status != ReservationStatus.ACTIVE:
        raise ReservationNotActiveError(
            f"Only ACTIVE reservations can be cancelled. "
            f"Current status: {reservation.status!r}."
        )

    reservation.status = ReservationStatus.CANCELLED
    reservation.save(update_fields=["status", "updated_at"])
    return reservation


@transaction.atomic
def checkout_from_reservations(
    user: User,
    reservation_ids: list,
    delivery_address: DeliveryAddress,
    delivery_fee: Decimal = Decimal("0.00"),
) -> Order:                                                   
                                               
    reservations = list(
        Reservation.objects
        .select_related("variant__product")
        .select_for_update()                                                 
        .filter(pk__in=reservation_ids, user=user, status=ReservationStatus.ACTIVE)
        .order_by("id")                                         
    )

    if len(reservations) != len(reservation_ids):
        found_ids = {str(r.pk) for r in reservations}
        missing = [str(rid) for rid in reservation_ids if str(rid) not in found_ids]
        raise ReservationConversionError(
            f"Reservations not found or not ACTIVE: {missing}. "
            "They may have expired or already been converted."
        )

                                                    
    if delivery_address.user_id != user.pk:
        raise ValueError("Delivery address does not belong to this user.")

                                                            
    variant_ids = sorted({str(r.variant_id) for r in reservations})
    locked_variants = {
        str(v.pk): v
        for v in ProductVariant.objects.select_for_update().filter(
            id__in=variant_ids
        )
    }

                                                                            
                                                                               
    now = timezone.now()
    for reservation in reservations:
                                                                           
                                                     
        if reservation.status != ReservationStatus.ACTIVE:
            raise ReservationConversionError(
                f"Reservation {reservation.pk} is no longer ACTIVE "
                f"(status={reservation.status!r}). It may have just been converted "
                "by a concurrent checkout."
            )
        if reservation.expires_at < now:
            raise ReservationConversionError(
                f"Reservation {reservation.pk} for variant "
                f"{reservation.variant.sku!r} has expired."
            )

                                             
    currencies = {r.variant.product.currency for r in reservations}
    if len(currencies) != 1:
        raise ValueError(
            "All items in a single order must share the same currency."
        )
    order_currency = currencies.pop()

                                             
    subtotal = Decimal("0.00")
    item_objects: list[OrderItem] = []
    price_snapshots: dict[str, Decimal] = {}

    for reservation in reservations:
        variant = locked_variants[str(reservation.variant_id)]
        price = variant.effective_price
        line_total = (price * reservation.quantity).quantize(Decimal("0.01"))
        subtotal += line_total
        price_snapshots[str(reservation.pk)] = price

                                    
    order = Order.objects.create(
        user=user,
        status=OrderStatus.CREATED,
        currency=order_currency,
        delivery_address=delivery_address,
        delivery_fee=delivery_fee,
        total_amount=Decimal("0.00"),                  
    )

                                                            
    for reservation in reservations:
        variant = locked_variants[str(reservation.variant_id)]
        price = price_snapshots[str(reservation.pk)]
        line_total = (price * reservation.quantity).quantize(Decimal("0.01"))
        sku_label = f" ({variant.sku})"

                                                                    
        ProductVariant.objects.filter(pk=variant.pk).update(
            stock=F("stock") - reservation.quantity
        )

        item_objects.append(
            OrderItem(
                order=order,
                product=reservation.variant.product,
                variant=variant,
                reservation=reservation,
                product_name_snapshot=reservation.variant.product.name + sku_label,
                product_price_snapshot=price,
                quantity=reservation.quantity,
                line_total=line_total,
            )
        )

    OrderItem.objects.bulk_create(item_objects)

                                    
    total_amount = subtotal.quantize(Decimal("0.01"))
    order.total_amount = total_amount
    order.status = OrderStatus.RESERVED
    order.save(update_fields=["total_amount", "status", "updated_at"])

                                             
                                                                             
                                                                       
    Reservation.objects.filter(
        pk__in=[r.pk for r in reservations]
    ).update(status=ReservationStatus.CONVERTED)

    return order


def expire_stale_reservations() -> int:
    now = timezone.now()
                                                                                       
    count = Reservation.objects.filter(
        status=ReservationStatus.ACTIVE,
        expires_at__lte=now,
    ).update(status=ReservationStatus.EXPIRED)
    return count
