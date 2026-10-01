from django.db.models.signals import post_save
from django.dispatch import receiver

from orders.models import Order
from payments.models import Payment, Refund

from .models import Notification
from .services import create_notification


def order_link(order):
    return f"/account/orders/" f"{order.order_number}"


def refund_link(refund):
    return f"/account/refunds/" f"{refund.reference}"


@receiver(
    post_save,
    sender=Payment,
    dispatch_uid="notifications_payment_status",
)
def payment_status_notification(
    sender,
    instance,
    **kwargs,
):
    payment = instance
    order = payment.order
    user = order.user

    if payment.status == Payment.Status.SUCCESSFUL:
        create_notification(
            user=user,
            event_type=(Notification.EventType.PAYMENT_CONFIRMED),
            title="Payment confirmed",
            message=(
                f"Your payment of "
                f"{payment.currency} {payment.amount} "
                f"for order {order.order_number} "
                "was confirmed successfully."
            ),
            link=order_link(order),
            metadata={
                "payment_reference": payment.reference,
                "order_number": order.order_number,
                "amount": str(payment.amount),
                "currency": payment.currency,
            },
            deduplication_key=(f"payment:{payment.pk}:confirmed"),
            email_subject=(f"Payment confirmed for " f"{order.order_number}"),
        )

    elif payment.status == Payment.Status.FAILED:
        create_notification(
            user=user,
            event_type=(Notification.EventType.PAYMENT_FAILED),
            title="Payment failed",
            message=(
                f"Your payment attempt for order "
                f"{order.order_number} was not successful. "
                "You may start another payment attempt "
                "if the order reservation is still active."
            ),
            link=order_link(order),
            metadata={
                "payment_reference": payment.reference,
                "order_number": order.order_number,
            },
            deduplication_key=(f"payment:{payment.pk}:failed"),
            email_subject=(f"Payment failed for " f"{order.order_number}"),
        )


@receiver(
    post_save,
    sender=Order,
    dispatch_uid="notifications_order_status",
)
def order_status_notification(
    sender,
    instance,
    **kwargs,
):
    order = instance
    user = order.user
    link = order_link(order)

    common_metadata = {
        "order_number": order.order_number,
        "status": order.status,
    }

    if order.status == Order.Status.CANCELLED:
        reason = (
            order.get_cancellation_reason_display()
            if order.cancellation_reason
            else "Order cancelled"
        )

        create_notification(
            user=user,
            event_type=(Notification.EventType.ORDER_CANCELLED),
            title="Order cancelled",
            message=(
                f"Order {order.order_number} was cancelled. " f"Reason: {reason}."
            ),
            link=link,
            metadata={
                **common_metadata,
                "cancellation_reason": (order.cancellation_reason),
            },
            deduplication_key=(f"order:{order.pk}:cancelled"),
            email_subject=(f"Order {order.order_number} cancelled"),
        )

    elif order.status == Order.Status.PROCESSING:
        create_notification(
            user=user,
            event_type=(Notification.EventType.ORDER_PROCESSING),
            title="Order is being processed",
            message=(
                f"Order {order.order_number} has been "
                "accepted and is being prepared."
            ),
            link=link,
            metadata=common_metadata,
            deduplication_key=(f"order:{order.pk}:processing"),
            email_subject=(f"Order {order.order_number} is processing"),
        )

    elif order.status == Order.Status.SHIPPED:
        shipment = getattr(
            order,
            "shipment",
            None,
        )

        carrier = shipment.carrier if shipment is not None else ""

        tracking_number = shipment.tracking_number if shipment is not None else ""

        create_notification(
            user=user,
            event_type=(Notification.EventType.ORDER_SHIPPED),
            title="Order shipped",
            message=(
                f"Order {order.order_number} has been "
                f"shipped with {carrier}. "
                f"Tracking number: {tracking_number}."
            ),
            link=link,
            metadata={
                **common_metadata,
                "carrier": carrier,
                "tracking_number": tracking_number,
            },
            deduplication_key=(f"order:{order.pk}:shipped"),
            email_subject=(f"Order {order.order_number} has shipped"),
        )

    elif order.status == Order.Status.DELIVERED:
        create_notification(
            user=user,
            event_type=(Notification.EventType.ORDER_DELIVERED),
            title="Order delivered",
            message=(f"Order {order.order_number} has been " "marked as delivered."),
            link=link,
            metadata=common_metadata,
            deduplication_key=(f"order:{order.pk}:delivered"),
            email_subject=(f"Order {order.order_number} delivered"),
        )


@receiver(
    post_save,
    sender=Refund,
    dispatch_uid="notifications_refund_status",
)
def refund_status_notification(
    sender,
    instance,
    **kwargs,
):
    refund = instance
    payment = refund.payment
    order = payment.order
    user = order.user
    link = refund_link(refund)

    common_metadata = {
        "refund_reference": refund.reference,
        "payment_reference": payment.reference,
        "order_number": order.order_number,
        "amount": str(refund.amount),
        "currency": refund.currency,
        "status": refund.status,
    }

    if refund.status == Refund.Status.PENDING:
        create_notification(
            user=user,
            event_type=(Notification.EventType.REFUND_INITIATED),
            title="Refund initiated",
            message=(
                f"Your refund of "
                f"{refund.currency} {refund.amount} "
                f"for order {order.order_number} "
                "has been submitted."
            ),
            link=link,
            metadata=common_metadata,
            deduplication_key=(f"refund:{refund.pk}:pending"),
            email_subject=(f"Refund started for " f"{order.order_number}"),
        )

    elif refund.status == Refund.Status.PROCESSING:
        create_notification(
            user=user,
            event_type=(Notification.EventType.REFUND_PROCESSING),
            title="Refund processing",
            message=(
                f"Your refund for order " f"{order.order_number} is being processed."
            ),
            link=link,
            metadata=common_metadata,
            deduplication_key=(f"refund:{refund.pk}:processing"),
            email_subject=(f"Refund processing for " f"{order.order_number}"),
        )

    elif refund.status == Refund.Status.NEEDS_ATTENTION:
        create_notification(
            user=user,
            event_type=(Notification.EventType.REFUND_NEEDS_ATTENTION),
            title="Refund requires attention",
            message=(
                f"The refund for order "
                f"{order.order_number} requires review. "
                "Our staff will investigate it."
            ),
            link=link,
            metadata=common_metadata,
            deduplication_key=(f"refund:{refund.pk}:needs_attention"),
            email_subject=(f"Refund update for " f"{order.order_number}"),
        )

    elif refund.status == Refund.Status.PROCESSED:
        create_notification(
            user=user,
            event_type=(Notification.EventType.REFUND_PROCESSED),
            title="Refund processed",
            message=(
                f"Your refund of "
                f"{refund.currency} {refund.amount} "
                f"for order {order.order_number} "
                "has been processed successfully."
            ),
            link=link,
            metadata=common_metadata,
            deduplication_key=(f"refund:{refund.pk}:processed"),
            email_subject=(f"Refund processed for " f"{order.order_number}"),
        )

    elif refund.status == Refund.Status.FAILED:
        create_notification(
            user=user,
            event_type=(Notification.EventType.REFUND_FAILED),
            title="Refund unsuccessful",
            message=(
                f"The refund for order "
                f"{order.order_number} could not be "
                "completed. Our staff will review it."
            ),
            link=link,
            metadata=common_metadata,
            deduplication_key=(f"refund:{refund.pk}:failed"),
            email_subject=(f"Refund update for " f"{order.order_number}"),
        )