import uuid

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import Q

from orders.models import Order


def generate_payment_reference():
    return f"PAY-{uuid.uuid4().hex.upper()}"


def generate_refund_reference():
    return f"REF-{uuid.uuid4().hex.upper()}"


class Payment(models.Model):
    class Provider(models.TextChoices):
        PAYSTACK = "paystack", "Paystack"

    class Status(models.TextChoices):
        INITIALIZED = "initialized", "Initialized"
        PENDING = "pending", "Pending"
        SUCCESSFUL = "successful", "Successful"
        FAILED = "failed", "Failed"
        ABANDONED = "abandoned", "Abandoned"
        REVERSED = "reversed", "Reversed"
        REFUNDED = "refunded", "Refunded"

    order = models.ForeignKey(
        Order,
        on_delete=models.PROTECT,
        related_name="payments",
    )

    provider = models.CharField(
        max_length=20,
        choices=Provider.choices,
        default=Provider.PAYSTACK,
    )

    reference = models.CharField(
        max_length=100,
        unique=True,
        default=generate_payment_reference,
        editable=False,
    )

    idempotency_key = models.UUIDField(
        default=uuid.uuid4,
        editable=False,
    )

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.INITIALIZED,
    )

    provider_status = models.CharField(max_length=30, blank=True)

    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(0)],
    )

    amount_subunit = models.PositiveBigIntegerField(
        validators=[MinValueValidator(1)],
    )

    currency = models.CharField(max_length=3, default="NGN")

    authorization_url = models.URLField(max_length=500, blank=True)
    access_code = models.CharField(max_length=100, blank=True)

    provider_transaction_id = models.BigIntegerField(
        unique=True,
        null=True,
        blank=True,
    )

    channel = models.CharField(max_length=30, blank=True)
    gateway_response = models.CharField(max_length=255, blank=True)
    failure_message = models.TextField(blank=True)
    initialization_response = models.JSONField(default=dict, blank=True)
    verification_response = models.JSONField(default=dict, blank=True)
    paid_at = models.DateTimeField(null=True, blank=True)
    verified_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["order", "idempotency_key"],
                name="unique_payment_key_per_order",
            ),
            models.UniqueConstraint(
                fields=["order"],
                condition=Q(status="successful"),
                name="one_successful_payment_per_order",
            ),
            models.UniqueConstraint(
                fields=["order"],
                condition=Q(status__in=["initialized", "pending"]),
                name="one_active_payment_per_order",
            ),
            models.CheckConstraint(
                condition=Q(amount__gte=0),
                name="payment_amount_nonnegative",
            ),
            models.CheckConstraint(
                condition=Q(amount_subunit__gt=0),
                name="payment_subunit_positive",
            ),
        ]
        indexes = [
            models.Index(
                fields=["order", "status"],
                name="payment_order_status_idx",
            ),
            models.Index(
                fields=["provider", "status"],
                name="payment_provider_status_idx",
            ),
        ]

    def __str__(self):
        return f"{self.reference} — {self.get_status_display()}"


class Refund(models.Model):
    class Status(models.TextChoices):
        INITIALIZED = "initialized", "Initialized"
        PENDING = "pending", "Pending"
        PROCESSING = "processing", "Processing"
        NEEDS_ATTENTION = "needs_attention", "Needs attention"
        PROCESSED = "processed", "Processed"
        FAILED = "failed", "Failed"

    payment = models.OneToOneField(
        Payment,
        on_delete=models.PROTECT,
        related_name="refund",
    )

    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="requested_refunds",
        null=True,
        blank=True,
    )

    requested_by_email = models.EmailField(blank=True)

    reference = models.CharField(
        max_length=100,
        unique=True,
        default=generate_refund_reference,
        editable=False,
    )

    provider = models.CharField(
        max_length=20,
        choices=Payment.Provider.choices,
        default=Payment.Provider.PAYSTACK,
    )

    provider_refund_id = models.CharField(
        max_length=100,
        unique=True,
        null=True,
        blank=True,
    )

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.INITIALIZED,
    )

    provider_status = models.CharField(max_length=30, blank=True)

    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(0)],
    )

    amount_subunit = models.PositiveBigIntegerField(
        validators=[MinValueValidator(1)],
    )

    currency = models.CharField(max_length=3)
    reason = models.TextField(max_length=1000)
    failure_message = models.TextField(blank=True)
    initialization_response = models.JSONField(default=dict, blank=True)
    latest_webhook_payload = models.JSONField(default=dict, blank=True)
    processed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.CheckConstraint(
                condition=Q(amount__gt=0),
                name="refund_amount_positive",
            ),
            models.CheckConstraint(
                condition=Q(amount_subunit__gt=0),
                name="refund_subunit_positive",
            ),
        ]
        indexes = [
            models.Index(
                fields=["provider", "status"],
                name="refund_provider_status_idx",
            ),
            models.Index(
                fields=["status", "created_at"],
                name="refund_status_created_idx",
            ),
        ]

    def __str__(self):
        return f"{self.reference} — {self.get_status_display()}"


class WebhookEvent(models.Model):
    provider = models.CharField(
        max_length=20,
        choices=Payment.Provider.choices,
        default=Payment.Provider.PAYSTACK,
    )
    event_type = models.CharField(max_length=100)
    reference = models.CharField(max_length=100, blank=True, db_index=True)
    payload_hash = models.CharField(max_length=64, unique=True)
    payload = models.JSONField(default=dict, blank=True)
    processed = models.BooleanField(default=False)
    processed_at = models.DateTimeField(null=True, blank=True)
    processing_error = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(
                fields=["provider", "event_type"],
                name="webhook_provider_event_idx",
            ),
            models.Index(
                fields=["processed", "created_at"],
                name="webhook_processed_time_idx",
            ),
        ]

    def __str__(self):
        return (
            f"{self.provider}: {self.event_type} — "
            f"{self.reference or 'no reference'}"
        )
