from django.conf import settings
from django.db import models
from django.db.models import F, Q

from orders.models import Order


class Shipment(models.Model):
    class Status(models.TextChoices):
        PREPARING = "preparing", "Preparing"
        SHIPPED = "shipped", "Shipped"
        DELIVERED = "delivered", "Delivered"
        FAILED = "failed", "Failed"
        RETURNED = "returned", "Returned"

    order = models.OneToOneField(
        Order,
        on_delete=models.PROTECT,
        related_name="shipment",
    )

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PREPARING,
    )

    carrier = models.CharField(
        max_length=100,
        blank=True,
        default="",
    )

    tracking_number = models.CharField(
        max_length=100,
        blank=True,
        default="",
    )

    shipped_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    delivered_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="created_shipments",
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        ordering = ["-created_at"]

        constraints = [
            models.UniqueConstraint(
                fields=["tracking_number"],
                condition=~Q(tracking_number=""),
                name="unique_nonempty_tracking_number",
            ),
            models.CheckConstraint(
                condition=(
                    ~Q(
                        status__in=[
                            "shipped",
                            "delivered",
                        ]
                    )
                    | (~Q(carrier="") & ~Q(tracking_number=""))
                ),
                name="shipment_tracking_required",
            ),
            models.CheckConstraint(
                condition=(~Q(status="shipped") | Q(shipped_at__isnull=False)),
                name="shipment_shipped_time_required",
            ),
            models.CheckConstraint(
                condition=(
                    ~Q(status="delivered")
                    | (Q(shipped_at__isnull=False) & Q(delivered_at__isnull=False))
                ),
                name="shipment_delivery_times_required",
            ),
            models.CheckConstraint(
                condition=(
                    Q(delivered_at__isnull=True)
                    | Q(shipped_at__isnull=True)
                    | Q(delivered_at__gte=F("shipped_at"))
                ),
                name="shipment_delivery_after_shipping",
            ),
        ]

        indexes = [
            models.Index(
                fields=["status", "created_at"],
                name="shipment_status_time_idx",
            ),
            models.Index(
                fields=["carrier", "status"],
                name="shipment_carrier_status_idx",
            ),
        ]

    def __str__(self):
        return (
            f"Shipment for {self.order.order_number} — " f"{self.get_status_display()}"
        )
