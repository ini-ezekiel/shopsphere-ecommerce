from django.db import transaction
from django.utils import timezone

from orders.models import (
    Order,
    OrderStatusHistory,
)
from payments.models import (
    Payment,
    Refund,
)

from .models import Shipment


class FulfillmentError(Exception):
    def __init__(self, message):
        self.message = message
        super().__init__(message)


ALLOWED_TRANSITIONS = {
    Order.Status.CONFIRMED: Order.Status.PROCESSING,
    Order.Status.PROCESSING: Order.Status.SHIPPED,
    Order.Status.SHIPPED: Order.Status.DELIVERED,
}


REFUND_BLOCKING_STATUSES = {
    Refund.Status.INITIALIZED,
    Refund.Status.PENDING,
    Refund.Status.PROCESSING,
    Refund.Status.NEEDS_ATTENTION,
    Refund.Status.PROCESSED,
}


def _validate_staff_user(user):
    if (
        user is None
        or not user.is_authenticated
        or not user.is_active
        or not user.is_staff
    ):
        raise FulfillmentError("Only active staff members can update order fulfilment.")


def _validate_shipping_details(
    *,
    carrier,
    tracking_number,
):
    carrier = str(carrier or "").strip()
    tracking_number = str(tracking_number or "").strip()

    if not carrier:
        raise FulfillmentError("A carrier is required when shipping an order.")

    if not tracking_number:
        raise FulfillmentError("A tracking number is required when shipping an order.")

    if len(carrier) > 100:
        raise FulfillmentError("The carrier cannot exceed 100 characters.")

    if len(tracking_number) > 100:
        raise FulfillmentError("The tracking number cannot exceed 100 characters.")

    return carrier, tracking_number


def _validate_refund_status(order):
    refund = (
        Refund.objects.select_for_update()
        .filter(
            payment__order=order,
            status__in=REFUND_BLOCKING_STATUSES,
        )
        .first()
    )

    if refund is None:
        return

    if refund.status == Refund.Status.PROCESSED:
        raise FulfillmentError(
            "This order has been refunded and cannot continue " "through fulfilment."
        )

    if refund.status == Refund.Status.NEEDS_ATTENTION:
        raise FulfillmentError(
            "This order has a refund that requires staff attention. "
            "Resolve the refund before continuing fulfilment."
        )

    raise FulfillmentError(
        "This order has an active refund and cannot continue " "through fulfilment."
    )


@transaction.atomic
def transition_order_status(
    *,
    order_number,
    new_status,
    changed_by,
    note="",
    carrier="",
    tracking_number="",
):
    _validate_staff_user(changed_by)

    new_status = str(new_status or "").strip()
    note = str(note or "").strip()

    allowed_target_statuses = {
        Order.Status.PROCESSING,
        Order.Status.SHIPPED,
        Order.Status.DELIVERED,
    }

    if new_status not in allowed_target_statuses:
        raise FulfillmentError(
            "The requested order status is not a valid " "fulfilment status."
        )

    if len(note) > 2000:
        raise FulfillmentError("The status note cannot exceed 2000 characters.")

    try:
        order = (
            Order.objects.select_for_update()
            .select_related("user")
            .get(order_number=order_number)
        )
    except Order.DoesNotExist as error:
        raise FulfillmentError("Order not found.") from error

    shipment = Shipment.objects.select_for_update().filter(order=order).first()

    # Repeating an already completed transition is idempotent.
    # It does not create another history entry.
    if order.status == new_status:
        return order, shipment, False

    expected_status = ALLOWED_TRANSITIONS.get(order.status)

    if expected_status != new_status:
        raise FulfillmentError(
            f"An order with status "
            f"'{order.get_status_display()}' cannot be "
            f"changed to "
            f"'{dict(Order.Status.choices).get(new_status, new_status)}'."
        )

    if order.inventory_status != Order.InventoryStatus.COMMITTED:
        raise FulfillmentError("The order inventory has not been committed.")

    _validate_refund_status(order)

    payment_succeeded = Payment.objects.filter(
        order=order,
        status=Payment.Status.SUCCESSFUL,
    ).exists()

    if not payment_succeeded:
        raise FulfillmentError("The order does not have a successful payment.")

    transition_time = timezone.now()
    previous_status = order.status

    if new_status == Order.Status.PROCESSING:
        if shipment is None:
            shipment = Shipment.objects.create(
                order=order,
                status=Shipment.Status.PREPARING,
                created_by=changed_by,
            )
        elif shipment.status != Shipment.Status.PREPARING:
            raise FulfillmentError("The shipment is not in the preparing state.")

    elif new_status == Order.Status.SHIPPED:
        carrier, tracking_number = _validate_shipping_details(
            carrier=carrier,
            tracking_number=tracking_number,
        )

        duplicate_tracking_number = (
            Shipment.objects.exclude(order=order)
            .filter(
                tracking_number=tracking_number,
            )
            .exists()
        )

        if duplicate_tracking_number:
            raise FulfillmentError("This tracking number is already in use.")

        if shipment is None:
            raise FulfillmentError(
                "The order must be processed before it can be shipped."
            )

        if shipment.status != Shipment.Status.PREPARING:
            raise FulfillmentError("The shipment is not ready to be shipped.")

        shipment.status = Shipment.Status.SHIPPED
        shipment.carrier = carrier
        shipment.tracking_number = tracking_number
        shipment.shipped_at = transition_time

        shipment.save(
            update_fields=[
                "status",
                "carrier",
                "tracking_number",
                "shipped_at",
                "updated_at",
            ]
        )

    elif new_status == Order.Status.DELIVERED:
        if shipment is None:
            raise FulfillmentError("The order has no shipment record.")

        if shipment.status != Shipment.Status.SHIPPED:
            raise FulfillmentError("Only a shipped order can be marked as delivered.")

        if shipment.shipped_at is None:
            raise FulfillmentError("The shipment has no shipping timestamp.")

        shipment.status = Shipment.Status.DELIVERED
        shipment.delivered_at = transition_time

        shipment.save(
            update_fields=[
                "status",
                "delivered_at",
                "updated_at",
            ]
        )

    order.status = new_status

    order.save(
        update_fields=[
            "status",
            "updated_at",
        ]
    )

    OrderStatusHistory.objects.create(
        order=order,
        from_status=previous_status,
        to_status=new_status,
        changed_by=changed_by,
        changed_by_email=changed_by.email,
        note=note,
    )

    order = (
        Order.objects.select_related("shipment")
        .prefetch_related("status_history")
        .get(pk=order.pk)
    )

    return order, order.shipment, True
