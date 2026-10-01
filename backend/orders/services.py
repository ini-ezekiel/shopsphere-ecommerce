from decimal import Decimal

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from addresses.models import ShippingAddress
from carts.models import Cart, CartItem
from products.models import Inventory

from .models import Order, OrderItem


class CheckoutError(Exception):
    def __init__(self, message):
        self.message = message
        super().__init__(message)


class OrderCancellationError(Exception):
    def __init__(self, message):
        self.message = message
        super().__init__(message)


def get_existing_order(user, idempotency_key):
    return (
        Order.objects.filter(
            user=user,
            idempotency_key=idempotency_key,
        )
        .prefetch_related("items")
        .first()
    )


@transaction.atomic
def create_checkout_order(
    *,
    user,
    shipping_address,
    idempotency_key,
):
    existing_order = get_existing_order(
        user=user,
        idempotency_key=idempotency_key,
    )

    if existing_order is not None:
        return existing_order, False

    try:
        cart = Cart.objects.select_for_update().get(user=user)
    except Cart.DoesNotExist as error:
        raise CheckoutError("Your cart is empty.") from error

    # Check again after locking the cart. Another request may have
    # completed checkout while this request was waiting for the lock.
    existing_order = get_existing_order(
        user=user,
        idempotency_key=idempotency_key,
    )

    if existing_order is not None:
        return existing_order, False

    try:
        address = (
            ShippingAddress.objects.select_for_update()
            .select_related("delivery_location")
            .get(
                pk=shipping_address.pk,
                user=user,
                delivery_location__is_active=True,
            )
        )
    except ShippingAddress.DoesNotExist as error:
        raise CheckoutError("The selected shipping address is unavailable.") from error

    cart_items = list(
        CartItem.objects.select_for_update().filter(cart=cart).order_by("variant_id")
    )

    if not cart_items:
        raise CheckoutError("Your cart is empty.")

    variant_ids = [item.variant_id for item in cart_items]

    inventories = list(
        Inventory.objects.select_for_update(of=("self",))
        .select_related(
            "variant__product__category",
            "variant__product__brand",
        )
        .filter(variant_id__in=variant_ids)
        .order_by("variant_id")
    )

    inventory_by_variant_id = {
        inventory.variant_id: inventory for inventory in inventories
    }

    subtotal = Decimal("0.00")
    order_item_data = []
    inventory_update_time = timezone.now()

    for cart_item in cart_items:
        inventory = inventory_by_variant_id.get(cart_item.variant_id)

        if inventory is None:
            raise CheckoutError("One of the selected products has no inventory record.")

        variant = inventory.variant
        product = variant.product

        if not product.is_active:
            raise CheckoutError(f"{product.name} is no longer available.")

        if not product.category.is_active:
            raise CheckoutError(f"{product.name} is no longer available.")

        if product.brand is not None and not product.brand.is_active:
            raise CheckoutError(f"{product.name} is no longer available.")

        if not variant.is_active:
            raise CheckoutError(
                f"{product.name} — {variant.name} " "is no longer available."
            )

        available_quantity = inventory.quantity - inventory.reserved_quantity

        if cart_item.quantity > available_quantity:
            raise CheckoutError(
                f"Only {available_quantity} unit(s) of "
                f"{product.name} — {variant.name} "
                "are currently available."
            )

        unit_price = variant.current_price

        if unit_price < 0:
            raise CheckoutError(f"{product.name} has an invalid price.")

        line_total = unit_price * cart_item.quantity
        subtotal += line_total

        order_item_data.append(
            {
                "variant": variant,
                "product_name": product.name,
                "variant_name": variant.name,
                "sku": variant.sku,
                "attributes": dict(variant.attributes or {}),
                "unit_price": unit_price,
                "quantity": cart_item.quantity,
                "line_total": line_total,
            }
        )

        inventory.reserved_quantity += cart_item.quantity
        inventory.updated_at = inventory_update_time

    delivery_location = address.delivery_location
    shipping_fee = delivery_location.shipping_fee
    discount_amount = Decimal("0.00")

    total_amount = subtotal - discount_amount + shipping_fee

    reservation_minutes = getattr(
        settings,
        "ORDER_RESERVATION_MINUTES",
        30,
    )

    reservation_expires_at = timezone.now() + timezone.timedelta(
        minutes=reservation_minutes,
    )

    order = Order.objects.create(
        user=user,
        idempotency_key=idempotency_key,
        status=Order.Status.PENDING_PAYMENT,
        inventory_status=Order.InventoryStatus.RESERVED,
        shipping_address=address,
        recipient_name=address.recipient_name,
        phone_number=address.phone_number,
        address_line_1=address.address_line_1,
        address_line_2=address.address_line_2,
        landmark=address.landmark,
        postal_code=address.postal_code,
        city=delivery_location.city,
        state=delivery_location.state,
        country=address.country,
        estimated_delivery_days=(delivery_location.estimated_delivery_days),
        subtotal=subtotal,
        discount_amount=discount_amount,
        shipping_fee=shipping_fee,
        total_amount=total_amount,
        reservation_expires_at=reservation_expires_at,
    )

    OrderItem.objects.bulk_create(
        [
            OrderItem(
                order=order,
                **item_data,
            )
            for item_data in order_item_data
        ]
    )

    Inventory.objects.bulk_update(
        inventories,
        [
            "reserved_quantity",
            "updated_at",
        ],
    )

    CartItem.objects.filter(
        cart=cart,
    ).delete()

    order = Order.objects.prefetch_related("items").get(pk=order.pk)

    return order, True


def _release_reserved_inventory(order):
    order_items = list(
        OrderItem.objects.select_for_update().filter(order=order).order_by("variant_id")
    )

    variant_ids = [
        item.variant_id for item in order_items if item.variant_id is not None
    ]

    inventories = list(
        Inventory.objects.select_for_update(of=("self",))
        .filter(variant_id__in=variant_ids)
        .order_by("variant_id")
    )

    inventory_by_variant_id = {
        inventory.variant_id: inventory for inventory in inventories
    }

    inventory_update_time = timezone.now()

    for order_item in order_items:
        if order_item.variant_id is None:
            continue

        inventory = inventory_by_variant_id.get(order_item.variant_id)

        if inventory is None:
            raise OrderCancellationError(
                "The inventory reservation is inconsistent. " "Contact support."
            )

        if inventory.reserved_quantity < order_item.quantity:
            raise OrderCancellationError(
                "The inventory reservation is inconsistent. " "Contact support."
            )

        inventory.reserved_quantity -= order_item.quantity
        inventory.updated_at = inventory_update_time

    if inventories:
        Inventory.objects.bulk_update(
            inventories,
            [
                "reserved_quantity",
                "updated_at",
            ],
        )


@transaction.atomic
def cancel_pending_order(*, user, order_number):
    try:
        order = Order.objects.select_for_update().get(
            user=user,
            order_number=order_number,
        )
    except Order.DoesNotExist as error:
        raise OrderCancellationError("Order not found.") from error

    if (
        order.status == Order.Status.CANCELLED
        and order.inventory_status == Order.InventoryStatus.RELEASED
    ):
        order = Order.objects.prefetch_related("items").get(pk=order.pk)

        return order, False

    if order.status != Order.Status.PENDING_PAYMENT:
        raise OrderCancellationError("Only orders awaiting payment can be cancelled.")

    if order.inventory_status != Order.InventoryStatus.RESERVED:
        raise OrderCancellationError(
            "This order does not have an active " "inventory reservation."
        )

    _release_reserved_inventory(order)

    cancellation_time = timezone.now()

    order.status = Order.Status.CANCELLED
    order.inventory_status = Order.InventoryStatus.RELEASED
    order.cancelled_at = cancellation_time
    order.cancellation_reason = Order.CancellationReason.CUSTOMER_CANCELLED

    order.save(
        update_fields=[
            "status",
            "inventory_status",
            "cancelled_at",
            "cancellation_reason",
            "updated_at",
        ]
    )

    order = Order.objects.prefetch_related("items").get(pk=order.pk)

    return order, True

@transaction.atomic
def _expire_pending_order_locked(
    *,
    order_id,
    expiration_time,
):
    try:
        order = Order.objects.select_for_update().get(
            pk=order_id,
        )
    except Order.DoesNotExist:
        return None, False

    if order.status != Order.Status.PENDING_PAYMENT:
        return order, False

    if (
        order.inventory_status
        != Order.InventoryStatus.RESERVED
    ):
        return order, False

    if order.reservation_expires_at is None:
        return order, False

    if order.reservation_expires_at > expiration_time:
        return order, False

    _release_reserved_inventory(order)

    order.status = Order.Status.CANCELLED
    order.inventory_status = (
        Order.InventoryStatus.RELEASED
    )
    order.cancelled_at = expiration_time
    order.cancellation_reason = (
        Order.CancellationReason.PAYMENT_EXPIRED
    )

    order.save(
        update_fields=[
            "status",
            "inventory_status",
            "cancelled_at",
            "cancellation_reason",
            "updated_at",
        ]
    )

    order = Order.objects.prefetch_related(
        "items"
    ).get(pk=order.pk)

    return order, True


def expire_pending_order(
    *,
    order_id,
    current_time=None,
):
    expiration_time = current_time or timezone.now()

    try:
        order = Order.objects.get(pk=order_id)
    except Order.DoesNotExist:
        return None, False

    if order.status != Order.Status.PENDING_PAYMENT:
        return order, False

    if (
        order.inventory_status
        != Order.InventoryStatus.RESERVED
    ):
        return order, False

    if order.reservation_expires_at is None:
        return order, False

    if order.reservation_expires_at > expiration_time:
        return order, False

    # Imported here to avoid coupling the app modules while
    # Django is loading the order and payment applications.
    from payments.services import (
        PaymentVerificationError,
        reconcile_order_payment,
    )

    try:
        payment, payment_succeeded = (
            reconcile_order_payment(
                order_id=order.id,
            )
        )
    except PaymentVerificationError as error:
        raise OrderCancellationError(
            "The payment status could not be confirmed. "
            "Order expiration was postponed."
        ) from error

    if payment_succeeded:
        order = Order.objects.prefetch_related(
            "items"
        ).get(pk=order.id)

        return order, False

    return _expire_pending_order_locked(
        order_id=order.id,
        expiration_time=expiration_time,
    )