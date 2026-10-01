from django.conf import settings
from django.db import models


class Notification(models.Model):
    class EventType(models.TextChoices):
        PAYMENT_CONFIRMED = (
            "payment_confirmed",
            "Payment confirmed",
        )
        PAYMENT_FAILED = (
            "payment_failed",
            "Payment failed",
        )
        ORDER_CANCELLED = (
            "order_cancelled",
            "Order cancelled",
        )
        ORDER_PROCESSING = (
            "order_processing",
            "Order processing",
        )
        ORDER_SHIPPED = (
            "order_shipped",
            "Order shipped",
        )
        ORDER_DELIVERED = (
            "order_delivered",
            "Order delivered",
        )
        REFUND_INITIATED = (
            "refund_initiated",
            "Refund initiated",
        )
        REFUND_PROCESSING = (
            "refund_processing",
            "Refund processing",
        )
        REFUND_NEEDS_ATTENTION = (
            "refund_needs_attention",
            "Refund needs attention",
        )
        REFUND_PROCESSED = (
            "refund_processed",
            "Refund processed",
        )
        REFUND_FAILED = (
            "refund_failed",
            "Refund failed",
        )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notifications",
    )

    event_type = models.CharField(
        max_length=40,
        choices=EventType.choices,
    )

    title = models.CharField(max_length=150)
    message = models.TextField()

    link = models.CharField(
        max_length=500,
        blank=True,
    )

    metadata = models.JSONField(
        default=dict,
        blank=True,
    )

    deduplication_key = models.CharField(
        max_length=255,
        unique=True,
        null=True,
        blank=True,
    )

    read_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

        indexes = [
            models.Index(
                fields=["user", "read_at"],
                name="notification_user_read_idx",
            ),
            models.Index(
                fields=["user", "created_at"],
                name="notification_user_time_idx",
            ),
        ]

    @property
    def is_read(self):
        return self.read_at is not None

    def __str__(self):
        return f"{self.user.email} — " f"{self.get_event_type_display()}"
