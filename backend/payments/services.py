import hashlib

from datetime import timezone as datetime_timezone

from decimal import Decimal

from django.db import IntegrityError, transaction

from django.utils import timezone

from django.utils.dateparse import parse_datetime

from orders.models import (
    Order,
    OrderItem,
    OrderStatusHistory,
)

from products.models import Inventory

from .models import (
    Payment,
    Refund,
    WebhookEvent,
)

from .paystack import (
    PaystackAPIError,
    PaystackConfigurationError,
    initialize_transaction,
    verify_transaction,
    create_refund as create_paystack_refund,
)


class PaymentInitializationError(Exception):

    def __init__(self, message):

        self.message = message

        super().__init__(message)


class PaymentVerificationError(Exception):

    def __init__(self, message):

        self.message = message

        super().__init__(message)


class RefundProcessingError(Exception):

    def __init__(self, message):

        self.message = message

        super().__init__(message)


class WebhookProcessingError(Exception):

    def __init__(self, message):

        self.message = message

        super().__init__(message)


def amount_to_subunit(amount):

    amount_subunit = amount * Decimal("100")

    if amount_subunit != amount_subunit.to_integral_value():

        raise PaymentInitializationError(
            "The order total has an invalid currency value."
        )

    amount_subunit = int(amount_subunit)

    if amount_subunit <= 0:

        raise PaymentInitializationError("The order total must be greater than zero.")

    return amount_subunit


@transaction.atomic
def _prepare_payment(
    *,
    user,
    order_number,
    idempotency_key,
):

    try:

        order = Order.objects.select_for_update().get(
            user=user,
            order_number=order_number,
        )

    except Order.DoesNotExist as error:

        raise PaymentInitializationError("Order not found.") from error

    if order.status != Order.Status.PENDING_PAYMENT:

        raise PaymentInitializationError("This order is not awaiting payment.")

    if order.inventory_status != Order.InventoryStatus.RESERVED:

        raise PaymentInitializationError(
            "This order has no active inventory reservation."
        )

    if order.reservation_expires_at is None:

        raise PaymentInitializationError("This order has no payment deadline.")

    if order.reservation_expires_at <= timezone.now():

        raise PaymentInitializationError(
            "This order's payment reservation has expired."
        )

    existing_payment = Payment.objects.filter(
        order=order,
        idempotency_key=idempotency_key,
    ).first()

    if existing_payment is not None:

        if existing_payment.status in {
            Payment.Status.PENDING,
            Payment.Status.SUCCESSFUL,
        }:

            return existing_payment, False

        if existing_payment.status == Payment.Status.INITIALIZED:

            raise PaymentInitializationError(
                "Payment initialization is already in progress."
            )

        raise PaymentInitializationError(
            "This payment attempt can no longer be used. "
            "Start another attempt with a new idempotency key."
        )

    active_payment = Payment.objects.filter(
        order=order,
        status__in=[
            Payment.Status.INITIALIZED,
            Payment.Status.PENDING,
        ],
    ).first()

    if active_payment is not None:

        if (
            active_payment.status == Payment.Status.PENDING
            and active_payment.authorization_url
        ):

            return active_payment, False

        raise PaymentInitializationError(
            "Payment initialization is already in progress."
        )

    amount_subunit = amount_to_subunit(order.total_amount)

    payment = Payment.objects.create(
        order=order,
        idempotency_key=idempotency_key,
        status=Payment.Status.INITIALIZED,
        amount=order.total_amount,
        amount_subunit=amount_subunit,
        currency=order.currency,
    )

    return payment, True


@transaction.atomic
def _mark_payment_failed(
    *,
    payment_id,
    message,
    response_data=None,
):

    payment = Payment.objects.select_for_update().get(
        pk=payment_id,
    )

    if payment.status == Payment.Status.SUCCESSFUL:

        return payment

    provider_data = (
        response_data.get("data", {}) if isinstance(response_data, dict) else {}
    )

    payment.status = Payment.Status.FAILED

    payment.provider_status = str(provider_data.get("status", ""))

    payment.failure_message = message

    payment.initialization_response = (
        response_data if isinstance(response_data, dict) else {}
    )

    payment.save(
        update_fields=[
            "status",
            "provider_status",
            "failure_message",
            "initialization_response",
            "updated_at",
        ]
    )

    return payment


@transaction.atomic
def _complete_payment_initialization(
    *,
    payment_id,
    response_data,
):

    payment = (
        Payment.objects.select_for_update().select_related("order").get(pk=payment_id)
    )

    order = Order.objects.select_for_update().get(
        pk=payment.order_id,
    )

    if payment.status != Payment.Status.INITIALIZED:

        return payment, None

    if order.status != Order.Status.PENDING_PAYMENT:

        message = "The order is no longer awaiting payment."

        payment.status = Payment.Status.FAILED

        payment.failure_message = message

        payment.initialization_response = response_data

        payment.save(
            update_fields=[
                "status",
                "failure_message",
                "initialization_response",
                "updated_at",
            ]
        )

        return payment, message

    if order.inventory_status != Order.InventoryStatus.RESERVED:

        message = "The order inventory reservation is no longer active."

        payment.status = Payment.Status.FAILED

        payment.failure_message = message

        payment.initialization_response = response_data

        payment.save(
            update_fields=[
                "status",
                "failure_message",
                "initialization_response",
                "updated_at",
            ]
        )

        return payment, message

    if (
        order.reservation_expires_at is None
        or order.reservation_expires_at <= timezone.now()
    ):

        message = "The order's payment reservation has expired."

        payment.status = Payment.Status.FAILED

        payment.failure_message = message

        payment.initialization_response = response_data

        payment.save(
            update_fields=[
                "status",
                "failure_message",
                "initialization_response",
                "updated_at",
            ]
        )

        return payment, message

    data = response_data.get("data", {})

    returned_reference = data.get("reference")

    authorization_url = data.get("authorization_url")

    access_code = data.get("access_code")

    if returned_reference != payment.reference:

        message = "Paystack returned an unexpected payment reference."

        payment.status = Payment.Status.FAILED

        payment.failure_message = message

        payment.initialization_response = response_data

        payment.save(
            update_fields=[
                "status",
                "failure_message",
                "initialization_response",
                "updated_at",
            ]
        )

        return payment, message

    if not authorization_url or not access_code:

        message = "Paystack did not return complete checkout information."

        payment.status = Payment.Status.FAILED

        payment.failure_message = message

        payment.initialization_response = response_data

        payment.save(
            update_fields=[
                "status",
                "failure_message",
                "initialization_response",
                "updated_at",
            ]
        )

        return payment, message

    payment.status = Payment.Status.PENDING

    payment.provider_status = "pending"

    payment.authorization_url = authorization_url

    payment.access_code = access_code

    payment.initialization_response = response_data

    payment.failure_message = ""

    payment.save(
        update_fields=[
            "status",
            "provider_status",
            "authorization_url",
            "access_code",
            "initialization_response",
            "failure_message",
            "updated_at",
        ]
    )

    return payment, None


def initialize_order_payment(
    *,
    user,
    order_number,
    idempotency_key,
):

    payment, should_initialize = _prepare_payment(
        user=user,
        order_number=order_number,
        idempotency_key=idempotency_key,
    )

    if not should_initialize:

        return payment, False

    try:

        response_data = initialize_transaction(
            email=user.email,
            amount_subunit=payment.amount_subunit,
            reference=payment.reference,
            metadata={
                "order_number": order_number,
                "payment_reference": payment.reference,
            },
        )

    except PaystackConfigurationError as error:

        message = str(error)

        _mark_payment_failed(
            payment_id=payment.id,
            message=message,
        )

        raise PaymentInitializationError(message) from error

    except PaystackAPIError as error:

        _mark_payment_failed(
            payment_id=payment.id,
            message=error.message,
            response_data=error.response_data,
        )

        raise PaymentInitializationError(error.message) from error

    payment, completion_error = _complete_payment_initialization(
        payment_id=payment.id,
        response_data=response_data,
    )

    if completion_error is not None:

        raise PaymentInitializationError(completion_error)

    return payment, True


def _parse_paid_at(value):

    if not value or not isinstance(value, str):

        raise PaymentVerificationError("Paystack did not return a valid payment time.")

    paid_at = parse_datetime(value)

    if paid_at is None:

        raise PaymentVerificationError("Paystack returned an invalid payment time.")

    if timezone.is_naive(paid_at):

        paid_at = timezone.make_aware(
            paid_at,
            datetime_timezone.utc,
        )

    return paid_at


def _get_provider_transaction_id(data):

    provider_transaction_id = data.get("id")

    try:

        provider_transaction_id = int(provider_transaction_id)

    except (TypeError, ValueError) as error:

        raise PaymentVerificationError(
            "Paystack returned an invalid transaction ID."
        ) from error

    if provider_transaction_id <= 0:

        raise PaymentVerificationError("Paystack returned an invalid transaction ID.")

    return provider_transaction_id


@transaction.atomic
def _finalize_verified_payment(
    *,
    payment_id,
    response_data,
):

    payment_record = Payment.objects.only(
        "id",
        "order_id",
    ).get(pk=payment_id)

    # Keep lock ordering consistent:

    # Order -> Payment -> OrderItem -> Inventory.

    order = Order.objects.select_for_update().get(
        pk=payment_record.order_id,
    )

    payment = Payment.objects.select_for_update().get(
        pk=payment_id,
        order=order,
    )

    if payment.status == Payment.Status.SUCCESSFUL:

        return payment, False

    data = response_data.get("data")

    if not isinstance(data, dict):

        raise PaymentVerificationError(
            "Paystack returned an invalid verification response."
        )

    returned_reference = data.get("reference")

    if returned_reference != payment.reference:

        raise PaymentVerificationError("The verified payment reference does not match.")

    provider_status = str(data.get("status", "")).strip().lower()

    provider_transaction_id = _get_provider_transaction_id(data)

    verification_time = timezone.now()

    if provider_status != "success":

        status_mapping = {
            "failed": Payment.Status.FAILED,
            "abandoned": Payment.Status.ABANDONED,
            "reversed": Payment.Status.REVERSED,
        }

        payment.status = status_mapping.get(
            provider_status,
            Payment.Status.PENDING,
        )

        payment.provider_status = provider_status

        payment.provider_transaction_id = provider_transaction_id

        payment.channel = str(data.get("channel", ""))

        payment.gateway_response = str(data.get("gateway_response", ""))

        payment.verification_response = response_data

        payment.verified_at = verification_time

        payment.save(
            update_fields=[
                "status",
                "provider_status",
                "provider_transaction_id",
                "channel",
                "gateway_response",
                "verification_response",
                "verified_at",
                "updated_at",
            ]
        )

        return payment, False

    try:

        returned_amount = int(data.get("amount"))

    except (TypeError, ValueError) as error:

        raise PaymentVerificationError(
            "Paystack returned an invalid payment amount."
        ) from error

    if returned_amount != payment.amount_subunit:

        raise PaymentVerificationError(
            "The verified payment amount does not match " "the order total."
        )

    returned_currency = str(data.get("currency", "")).strip().upper()

    if returned_currency != payment.currency.upper():

        raise PaymentVerificationError("The verified payment currency does not match.")

    paid_at = _parse_paid_at(data.get("paid_at"))

    if order.reservation_expires_at is None:

        raise PaymentVerificationError("The order has no payment deadline.")

    # A payment verified after the deadline is still accepted if

    # Paystack confirms that the customer paid before the deadline.

    if paid_at > order.reservation_expires_at:

        raise PaymentVerificationError(
            "Payment was completed after the inventory " "reservation expired."
        )

    if order.status != Order.Status.PENDING_PAYMENT:

        raise PaymentVerificationError("The order is no longer awaiting payment.")

    if order.inventory_status != Order.InventoryStatus.RESERVED:

        raise PaymentVerificationError(
            "The order inventory reservation is no longer active."
        )

    order_items = list(
        OrderItem.objects.select_for_update().filter(order=order).order_by("variant_id")
    )

    if not order_items:

        raise PaymentVerificationError("The order contains no items.")

    variant_ids = []

    for order_item in order_items:

        if order_item.variant_id is None:

            raise PaymentVerificationError(
                "An ordered product no longer has an " "inventory record."
            )

        variant_ids.append(order_item.variant_id)

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

        inventory = inventory_by_variant_id.get(order_item.variant_id)

        if inventory is None:

            raise PaymentVerificationError(
                "An ordered product has no inventory record."
            )

        if inventory.reserved_quantity < order_item.quantity:

            raise PaymentVerificationError(
                "The inventory reservation is inconsistent. " "Contact support."
            )

        if inventory.quantity < order_item.quantity:

            raise PaymentVerificationError(
                "The available inventory is inconsistent. " "Contact support."
            )

        inventory.quantity -= order_item.quantity

        inventory.reserved_quantity -= order_item.quantity

        inventory.updated_at = inventory_update_time

    Inventory.objects.bulk_update(
        inventories,
        [
            "quantity",
            "reserved_quantity",
            "updated_at",
        ],
    )

    payment.status = Payment.Status.SUCCESSFUL

    payment.provider_status = provider_status

    payment.provider_transaction_id = provider_transaction_id

    payment.channel = str(data.get("channel", ""))

    payment.gateway_response = str(data.get("gateway_response", ""))

    payment.verification_response = response_data

    payment.paid_at = paid_at

    payment.verified_at = verification_time

    payment.failure_message = ""

    payment.save(
        update_fields=[
            "status",
            "provider_status",
            "provider_transaction_id",
            "channel",
            "gateway_response",
            "verification_response",
            "paid_at",
            "verified_at",
            "failure_message",
            "updated_at",
        ]
    )

    #
    previous_order_status = order.status
    order.status = Order.Status.CONFIRMED
    order.inventory_status = Order.InventoryStatus.COMMITTED
    order.save(
        update_fields=[
            "status",
            "inventory_status",
            "updated_at",
        ]
    )
    OrderStatusHistory.objects.create(
        order=order,
        from_status=previous_order_status,
        to_status=Order.Status.CONFIRMED,
        changed_by=None,
        changed_by_email="",
        note="Payment confirmed successfully.",
    )
    return payment, True


def verify_order_payment(
    *,
    user,
    reference,
):

    try:

        payment = Payment.objects.select_related("order").get(
            reference=reference,
            order__user=user,
        )

    except Payment.DoesNotExist as error:

        raise PaymentVerificationError("Payment not found.") from error

    if payment.status == Payment.Status.SUCCESSFUL:

        return payment, False

    try:

        response_data = verify_transaction(
            reference=payment.reference,
        )

    except PaystackConfigurationError as error:

        raise PaymentVerificationError(str(error)) from error

    except PaystackAPIError as error:

        raise PaymentVerificationError(error.message) from error

    return _finalize_verified_payment(
        payment_id=payment.id,
        response_data=response_data,
    )


# paystack hook


def _normalize_refund_status(value):

    value = str(value or "").strip().lower()

    status_mapping = {
        "pending": Refund.Status.PENDING,
        "processing": Refund.Status.PROCESSING,
        "needs-attention": Refund.Status.NEEDS_ATTENTION,
        "needs_attention": Refund.Status.NEEDS_ATTENTION,
        "processed": Refund.Status.PROCESSED,
        "failed": Refund.Status.FAILED,
    }

    return status_mapping.get(value)


def _get_refund_transaction_reference(data):

    transaction_data = data.get("transaction")

    if isinstance(transaction_data, dict):

        return str(transaction_data.get("reference", "")).strip()

    return str(data.get("transaction_reference", "")).strip()


@transaction.atomic
def _prepare_full_refund(
    *,
    payment_reference,
    requested_by,
    reason,
):

    if (
        requested_by is None
        or not requested_by.is_authenticated
        or not requested_by.is_active
        or not requested_by.is_staff
    ):

        raise RefundProcessingError("Only active staff members can initiate refunds.")

    reason = str(reason or "").strip()

    if not reason:

        raise RefundProcessingError("A refund reason is required.")

    if len(reason) > 1000:

        raise RefundProcessingError("The refund reason cannot exceed 1000 characters.")

    try:

        payment_record = Payment.objects.only(
            "id",
            "order_id",
        ).get(
            reference=payment_reference,
        )

    except Payment.DoesNotExist as error:

        raise RefundProcessingError("Payment not found.") from error

    # Preserve the existing lock order:

    # Order -> Payment -> Refund.

    order = Order.objects.select_for_update().get(
        pk=payment_record.order_id,
    )

    payment = (
        Payment.objects.select_for_update()
        .select_related("order")
        .get(
            pk=payment_record.id,
            order=order,
        )
    )

    existing_refund = Refund.objects.select_for_update().filter(payment=payment).first()

    if existing_refund is not None:

        if existing_refund.status == Refund.Status.INITIALIZED:

            raise RefundProcessingError("Refund initialization is already in progress.")

        return existing_refund, False

    if payment.status != Payment.Status.SUCCESSFUL:

        raise RefundProcessingError("Only successful payments can be refunded.")

    if payment.amount <= 0 or payment.amount_subunit <= 0:

        raise RefundProcessingError("The payment has an invalid refund amount.")

    if not payment.provider_transaction_id:

        raise RefundProcessingError("The payment has no verified provider transaction.")

    refund = Refund.objects.create(
        payment=payment,
        requested_by=requested_by,
        requested_by_email=requested_by.email,
        provider=payment.provider,
        status=Refund.Status.INITIALIZED,
        amount=payment.amount,
        amount_subunit=payment.amount_subunit,
        currency=payment.currency,
        reason=reason,
    )

    return refund, True


@transaction.atomic
def _mark_refund_failed(
    *,
    refund_id,
    message,
    response_data=None,
):

    refund = (
        Refund.objects.select_for_update().select_related("payment").get(pk=refund_id)
    )

    if refund.status == Refund.Status.PROCESSED:

        return refund

    data = response_data.get("data", {}) if isinstance(response_data, dict) else {}

    refund.status = Refund.Status.FAILED

    refund.provider_status = str(data.get("status", "")).strip().lower()

    refund.failure_message = message

    refund.initialization_response = (
        response_data if isinstance(response_data, dict) else {}
    )

    refund.save(
        update_fields=[
            "status",
            "provider_status",
            "failure_message",
            "initialization_response",
            "updated_at",
        ]
    )

    return refund


@transaction.atomic
def _complete_refund_initialization(
    *,
    refund_id,
    response_data,
):

    refund_record = Refund.objects.only(
        "id",
        "payment_id",
    ).get(pk=refund_id)

    payment_record = Payment.objects.only(
        "id",
        "order_id",
    ).get(pk=refund_record.payment_id)

    # Preserve lock ordering:

    # Order -> Payment -> Refund.

    order = Order.objects.select_for_update().get(
        pk=payment_record.order_id,
    )

    payment = Payment.objects.select_for_update().get(
        pk=payment_record.id,
        order=order,
    )

    refund = Refund.objects.select_for_update().get(
        pk=refund_record.id,
        payment=payment,
    )

    if refund.status != Refund.Status.INITIALIZED:

        return refund

    data = response_data.get("data")

    if not isinstance(data, dict):

        raise RefundProcessingError("Paystack returned an invalid refund response.")

    transaction_reference = _get_refund_transaction_reference(data)

    if transaction_reference != payment.reference:

        raise RefundProcessingError(
            "The refunded transaction reference does not match."
        )

    provider_refund_id = str(data.get("id", "")).strip()

    if not provider_refund_id:

        raise RefundProcessingError("Paystack returned an invalid refund ID.")

    try:

        returned_amount = int(data.get("amount"))

    except (TypeError, ValueError) as error:

        raise RefundProcessingError(
            "Paystack returned an invalid refund amount."
        ) from error

    if returned_amount != refund.amount_subunit:

        raise RefundProcessingError("The refund amount does not match the payment.")

    returned_currency = str(data.get("currency", "")).strip().upper()

    if returned_currency != refund.currency.upper():

        raise RefundProcessingError("The refund currency does not match the payment.")

    provider_status = str(data.get("status", "")).strip().lower()

    refund_status = _normalize_refund_status(
        provider_status,
    )

    if refund_status is None:

        raise RefundProcessingError("Paystack returned an unsupported refund status.")

    refund.provider_refund_id = provider_refund_id

    refund.status = refund_status

    refund.provider_status = provider_status

    refund.initialization_response = response_data

    refund.failure_message = ""

    refund_update_fields = [
        "provider_refund_id",
        "status",
        "provider_status",
        "initialization_response",
        "failure_message",
        "updated_at",
    ]

    if refund_status == Refund.Status.PROCESSED:

        refund.processed_at = timezone.now()

        refund_update_fields.append("processed_at")

        payment.status = Payment.Status.REFUNDED

        payment.provider_status = "reversed"

        payment.save(
            update_fields=[
                "status",
                "provider_status",
                "updated_at",
            ]
        )

    elif refund_status == Refund.Status.FAILED:

        payment.provider_status = "success"

        payment.save(
            update_fields=[
                "provider_status",
                "updated_at",
            ]
        )

    else:

        payment.provider_status = "reversal pending"

        payment.save(
            update_fields=[
                "provider_status",
                "updated_at",
            ]
        )

    refund.save(
        update_fields=refund_update_fields,
    )

    return refund


def initiate_full_refund(
    *,
    payment_reference,
    requested_by,
    reason,
):

    refund, should_initialize = _prepare_full_refund(
        payment_reference=payment_reference,
        requested_by=requested_by,
        reason=reason,
    )

    if not should_initialize:

        return refund, False

    payment = Payment.objects.select_related(
        "order",
    ).get(pk=refund.payment_id)

    try:

        response_data = create_paystack_refund(
            transaction_reference=payment.reference,
            amount_subunit=refund.amount_subunit,
            currency=refund.currency,
            customer_note=(
                "Your payment for order "
                f"{payment.order.order_number} "
                "is being refunded."
            ),
            merchant_note=(
                f"{refund.reason} | "
                f"Requested by {refund.requested_by_email} | "
                f"Local refund {refund.reference}"
            ),
        )

    except PaystackConfigurationError as error:

        message = str(error)

        _mark_refund_failed(
            refund_id=refund.id,
            message=message,
        )

        raise RefundProcessingError(message) from error

    except PaystackAPIError as error:

        _mark_refund_failed(
            refund_id=refund.id,
            message=error.message,
            response_data=error.response_data,
        )

        raise RefundProcessingError(error.message) from error

    try:

        refund = _complete_refund_initialization(
            refund_id=refund.id,
            response_data=response_data,
        )

    except RefundProcessingError as error:

        _mark_refund_failed(
            refund_id=refund.id,
            message=error.message,
            response_data=response_data,
        )

        raise

    return refund, True


def _get_or_create_webhook_event(
    *,
    payload,
    raw_body,
):

    payload_hash = hashlib.sha256(
        raw_body,
    ).hexdigest()

    event_type = str(payload.get("event", "")).strip()

    data = payload.get("data", {})

    reference = ""

    if isinstance(data, dict):

        if event_type.startswith("refund."):

            reference = _get_refund_transaction_reference(data)

        else:

            reference = str(data.get("reference", "")).strip()

    defaults = {
        "provider": Payment.Provider.PAYSTACK,
        "event_type": event_type,
        "reference": reference,
        "payload": payload,
    }

    try:

        with transaction.atomic():

            event, created = WebhookEvent.objects.get_or_create(
                payload_hash=payload_hash,
                defaults=defaults,
            )

    except IntegrityError:

        event = WebhookEvent.objects.get(
            payload_hash=payload_hash,
        )

        created = False

    return event, created


@transaction.atomic
def _mark_webhook_processed(
    *,
    event_id,
    processing_error="",
):

    event = WebhookEvent.objects.select_for_update().get(
        pk=event_id,
    )

    event.processed = True

    event.processed_at = timezone.now()

    event.processing_error = processing_error

    event.save(
        update_fields=[
            "processed",
            "processed_at",
            "processing_error",
        ]
    )

    return event


@transaction.atomic
def _mark_webhook_error(
    *,
    event_id,
    message,
):

    event = WebhookEvent.objects.select_for_update().get(
        pk=event_id,
    )

    if event.processed:

        return event

    event.processing_error = message

    event.save(
        update_fields=[
            "processing_error",
        ]
    )

    return event


REFUND_WEBHOOK_STATUSES = {
    "refund.pending": Refund.Status.PENDING,
    "refund.processing": Refund.Status.PROCESSING,
    "refund.needs-attention": (Refund.Status.NEEDS_ATTENTION),
    "refund.processed": Refund.Status.PROCESSED,
    "refund.failed": Refund.Status.FAILED,
}


def _find_refund_for_webhook(data):

    provider_refund_id = str(data.get("id", "")).strip()

    if provider_refund_id:

        refund = (
            Refund.objects.filter(
                provider_refund_id=provider_refund_id,
            )
            .select_related("payment")
            .first()
        )

        if refund is not None:

            return refund

    transaction_reference = _get_refund_transaction_reference(data)

    if not transaction_reference:

        return None

    return (
        Refund.objects.filter(
            payment__reference=transaction_reference,
        )
        .select_related("payment")
        .first()
    )


@transaction.atomic
def _apply_refund_webhook(
    *,
    refund_id,
    event_type,
    data,
    payload,
):

    refund_record = Refund.objects.only(
        "id",
        "payment_id",
    ).get(pk=refund_id)

    payment_record = Payment.objects.only(
        "id",
        "order_id",
    ).get(pk=refund_record.payment_id)

    # Preserve lock ordering:

    # Order -> Payment -> Refund.

    order = Order.objects.select_for_update().get(
        pk=payment_record.order_id,
    )

    payment = Payment.objects.select_for_update().get(
        pk=payment_record.id,
        order=order,
    )

    refund = Refund.objects.select_for_update().get(
        pk=refund_record.id,
        payment=payment,
    )

    target_status = REFUND_WEBHOOK_STATUSES.get(
        event_type,
    )

    if target_status is None:

        raise RefundProcessingError("The refund webhook status is unsupported.")

    provider_refund_id = str(data.get("id", "")).strip()

    if not provider_refund_id:

        raise RefundProcessingError("The refund webhook ID is missing.")

    if refund.provider_refund_id and refund.provider_refund_id != provider_refund_id:

        raise RefundProcessingError("The refund webhook ID does not match.")

    transaction_reference = _get_refund_transaction_reference(data)

    if transaction_reference and transaction_reference != payment.reference:

        raise RefundProcessingError("The refund webhook transaction does not match.")

    try:

        returned_amount = int(data.get("amount"))

    except (TypeError, ValueError) as error:

        raise RefundProcessingError("The refund webhook amount is invalid.") from error

    if returned_amount != refund.amount_subunit:

        raise RefundProcessingError("The refund webhook amount does not match.")

    returned_currency = str(data.get("currency", "")).strip().upper()

    if returned_currency != refund.currency.upper():

        raise RefundProcessingError("The refund webhook currency does not match.")

    data_status = str(data.get("status", "")).strip().lower()

    if data_status:

        normalized_data_status = _normalize_refund_status(data_status)

        if normalized_data_status != target_status:

            raise RefundProcessingError(
                "The refund webhook status does not match " "its event type."
            )

    # Never downgrade a refund after Paystack has supplied

    # a final processed or failed status.

    if refund.status in {
        Refund.Status.PROCESSED,
        Refund.Status.FAILED,
    }:

        return refund, False

    refund.provider_refund_id = provider_refund_id

    refund.status = target_status

    refund.provider_status = data_status or (event_type.removeprefix("refund."))

    refund.latest_webhook_payload = payload

    refund.failure_message = ""

    refund_update_fields = [
        "provider_refund_id",
        "status",
        "provider_status",
        "latest_webhook_payload",
        "failure_message",
        "updated_at",
    ]

    if target_status == Refund.Status.PROCESSED:

        refund.processed_at = timezone.now()

        refund_update_fields.append("processed_at")

        payment.status = Payment.Status.REFUNDED

        payment.provider_status = "reversed"

        payment.save(
            update_fields=[
                "status",
                "provider_status",
                "updated_at",
            ]
        )

    elif target_status == Refund.Status.FAILED:

        failure_message = str(
            data.get("reason")
            or data.get("message")
            or "Paystack could not process the refund."
        ).strip()

        refund.failure_message = failure_message

        if "failure_message" not in refund_update_fields:

            refund_update_fields.append("failure_message")

        payment.provider_status = "success"

        payment.save(
            update_fields=[
                "provider_status",
                "updated_at",
            ]
        )

    else:

        payment.provider_status = "reversal pending"

        payment.save(
            update_fields=[
                "provider_status",
                "updated_at",
            ]
        )

    refund.save(
        update_fields=refund_update_fields,
    )

    return refund, True


def _process_refund_webhook(
    *,
    event_type,
    payload,
):

    data = payload.get("data")

    if not isinstance(data, dict):

        raise RefundProcessingError("The refund webhook data is invalid.")

    refund = _find_refund_for_webhook(data)

    if refund is None:

        return None, False

    return _apply_refund_webhook(
        refund_id=refund.id,
        event_type=event_type,
        data=data,
        payload=payload,
    )


def process_paystack_webhook(
    *,
    payload,
    raw_body,
):

    if not isinstance(payload, dict):

        raise WebhookProcessingError("The webhook payload must be an object.")

    event, created = _get_or_create_webhook_event(
        payload=payload,
        raw_body=raw_body,
    )

    if event.processed:

        return event, False

    event_type = str(payload.get("event", "")).strip()

    if not event_type:

        message = "The webhook event type is missing."

        _mark_webhook_error(
            event_id=event.id,
            message=message,
        )

        raise WebhookProcessingError(message)

    if event_type in REFUND_WEBHOOK_STATUSES:

        try:

            refund, updated = _process_refund_webhook(
                event_type=event_type,
                payload=payload,
            )

        except RefundProcessingError as error:

            _mark_webhook_error(
                event_id=event.id,
                message=error.message,
            )

            raise WebhookProcessingError(error.message) from error

        if refund is None:

            event = _mark_webhook_processed(
                event_id=event.id,
                processing_error=("No local refund matched this event."),
            )

            return event, created

        event = _mark_webhook_processed(
            event_id=event.id,
        )

        return event, updated

    # Other Paystack events are safely recorded and ignored.

    if event_type != "charge.success":

        event = _mark_webhook_processed(
            event_id=event.id,
        )

        return event, created

    data = payload.get("data")

    if not isinstance(data, dict):

        message = "The webhook transaction data is invalid."

        _mark_webhook_error(
            event_id=event.id,
            message=message,
        )

        raise WebhookProcessingError(message)

    reference = str(data.get("reference", "")).strip()

    if not reference:

        message = "The webhook payment reference is missing."

        _mark_webhook_error(
            event_id=event.id,
            message=message,
        )

        raise WebhookProcessingError(message)

    try:

        payment = Payment.objects.get(
            reference=reference,
        )

    except Payment.DoesNotExist:

        # The event is genuine but does not belong to a

        # transaction created by this application.

        event = _mark_webhook_processed(
            event_id=event.id,
            processing_error=("No local payment matched this reference."),
        )

        return event, created

    try:

        verification_response = verify_transaction(
            reference=payment.reference,
        )

    except PaystackConfigurationError as error:

        message = str(error)

        _mark_webhook_error(
            event_id=event.id,
            message=message,
        )

        raise WebhookProcessingError(message) from error

    except PaystackAPIError as error:

        message = error.message

        _mark_webhook_error(
            event_id=event.id,
            message=message,
        )

        raise WebhookProcessingError(message) from error

    try:

        verified_payment, finalized = _finalize_verified_payment(
            payment_id=payment.id,
            response_data=verification_response,
        )

    except PaymentVerificationError as error:

        _mark_webhook_error(
            event_id=event.id,
            message=error.message,
        )

        raise WebhookProcessingError(error.message) from error

    if verified_payment.status != Payment.Status.SUCCESSFUL:

        message = "Paystack has not confirmed the payment " "as successful."

        _mark_webhook_error(
            event_id=event.id,
            message=message,
        )

        raise WebhookProcessingError(message)

    event = _mark_webhook_processed(
        event_id=event.id,
    )

    return event, finalized


# This only checks pending payments. Failed or abandoned attempts will not prevent expiration.


def reconcile_order_payment(
    *,
    order_id,
):

    successful_payment = Payment.objects.filter(
        order_id=order_id,
        status=Payment.Status.SUCCESSFUL,
    ).first()

    if successful_payment is not None:

        return successful_payment, True

    payment = (
        Payment.objects.filter(
            order_id=order_id,
            status=Payment.Status.PENDING,
        )
        .order_by("-created_at")
        .first()
    )

    if payment is None:

        return None, False

    try:

        response_data = verify_transaction(
            reference=payment.reference,
        )

    except PaystackConfigurationError as error:

        raise PaymentVerificationError(str(error)) from error

    except PaystackAPIError as error:

        raise PaymentVerificationError(error.message) from error

    verified_payment, finalized = _finalize_verified_payment(
        payment_id=payment.id,
        response_data=response_data,
    )

    payment_succeeded = verified_payment.status == Payment.Status.SUCCESSFUL

    return verified_payment, payment_succeeded
