import uuid

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import F, Q

from addresses.models import ShippingAddress
from products.models import ProductVariant


def generate_order_number():
    return f"ORD-{uuid.uuid4().hex[:20].upper()}"


class Order(models.Model):
    class Status(models.TextChoices):
        PENDING_PAYMENT = (
            "pending_payment",
            "Pending payment",
        )
        CONFIRMED = "confirmed", "Confirmed"
        PROCESSING = "processing", "Processing"
        SHIPPED = "shipped", "Shipped"
        DELIVERED = "delivered", "Delivered"
        CANCELLED = "cancelled", "Cancelled"

    class InventoryStatus(models.TextChoices):
        NOT_RESERVED = "not_reserved", "Not reserved"
        RESERVED = "reserved", "Reserved"
        COMMITTED = "committed", "Committed"
        RELEASED = "released", "Released"

    class CancellationReason(models.TextChoices):
        CUSTOMER_CANCELLED = (
            "customer_cancelled",
            "Cancelled by customer",
        )
        PAYMENT_EXPIRED = (
            "payment_expired",
            "Payment reservation expired",
        )
        STAFF_CANCELLED = (
            "staff_cancelled",
            "Cancelled by staff",
        )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="orders",
    )

    order_number = models.CharField(
        max_length=24,
        unique=True,
        default=generate_order_number,
        editable=False,
    )

    idempotency_key = models.UUIDField(
        default=uuid.uuid4,
        editable=False,
    )

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING_PAYMENT,
    )

    inventory_status = models.CharField(
        max_length=20,
        choices=InventoryStatus.choices,
        default=InventoryStatus.NOT_RESERVED,
    )

    shipping_address = models.ForeignKey(
        ShippingAddress,
        on_delete=models.SET_NULL,
        related_name="orders",
        null=True,
        blank=True,
    )

    recipient_name = models.CharField(max_length=150)
    phone_number = models.CharField(max_length=20)

    address_line_1 = models.CharField(max_length=255)

    address_line_2 = models.CharField(
        max_length=255,
        blank=True,
    )

    landmark = models.CharField(
        max_length=255,
        blank=True,
    )

    postal_code = models.CharField(
        max_length=20,
        blank=True,
    )

    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)

    country = models.CharField(
        max_length=100,
        default="Nigeria",
    )

    estimated_delivery_days = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1)],
    )

    currency = models.CharField(
        max_length=3,
        default="NGN",
        editable=False,
    )

    subtotal = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(0)],
    )

    discount_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0)],
    )

    shipping_fee = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(0)],
    )

    total_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(0)],
    )

    reservation_expires_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    cancelled_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    cancellation_reason = models.CharField(
        max_length=30,
        choices=CancellationReason.choices,
        null=True,
        blank=True,
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

        constraints = [
            models.UniqueConstraint(
                fields=["user", "idempotency_key"],
                name="unique_checkout_key_per_user",
            ),
            models.CheckConstraint(
                condition=Q(subtotal__gte=0),
                name="order_nonnegative_subtotal",
            ),
            models.CheckConstraint(
                condition=Q(discount_amount__gte=0),
                name="order_nonnegative_discount",
            ),
            models.CheckConstraint(
                condition=Q(discount_amount__lte=F("subtotal")),
                name="order_discount_lte_subtotal",
            ),
            models.CheckConstraint(
                condition=Q(shipping_fee__gte=0),
                name="order_nonnegative_shipping",
            ),
            models.CheckConstraint(
                condition=Q(total_amount__gte=0),
                name="order_nonnegative_total",
            ),
        ]

        indexes = [
            models.Index(
                fields=["user", "status"],
                name="orders_user_status_idx",
            ),
            models.Index(
                fields=[
                    "status",
                    "reservation_expires_at",
                ],
                name="orders_status_expiry_idx",
            ),
        ]

    def __str__(self):
        return self.order_number


class OrderItem(models.Model):
    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name="items",
    )

    variant = models.ForeignKey(
        ProductVariant,
        on_delete=models.SET_NULL,
        related_name="order_items",
        null=True,
        blank=True,
    )

    product_name = models.CharField(max_length=255)
    variant_name = models.CharField(max_length=150)
    sku = models.CharField(max_length=100)

    attributes = models.JSONField(
        default=dict,
        blank=True,
    )

    unit_price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(0)],
    )

    quantity = models.PositiveIntegerField(
        validators=[MinValueValidator(1)],
    )

    line_total = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(0)],
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["id"]

        constraints = [
            models.CheckConstraint(
                condition=Q(quantity__gt=0),
                name="order_item_positive_quantity",
            ),
            models.CheckConstraint(
                condition=Q(unit_price__gte=0),
                name="order_item_nonnegative_price",
            ),
            models.CheckConstraint(
                condition=Q(line_total__gte=0),
                name="order_item_nonnegative_total",
            ),
            models.UniqueConstraint(
                fields=["order", "variant"],
                condition=Q(variant__isnull=False),
                name="unique_variant_per_order",
            ),
        ]

    def __str__(self):
        return f"{self.product_name} — " f"{self.variant_name} × {self.quantity}"


class OrderStatusHistory(models.Model):
    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name="status_history",
    )

    from_status = models.CharField(
        max_length=20,
        choices=Order.Status.choices,
    )

    to_status = models.CharField(
        max_length=20,
        choices=Order.Status.choices,
    )

    changed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="order_status_changes",
        null=True,
        blank=True,
    )

    changed_by_email = models.EmailField(
        blank=True,
    )

    note = models.TextField(
        blank=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    class Meta:
        ordering = ["created_at"]

        constraints = [
            models.CheckConstraint(
                condition=~Q(
                    from_status=F("to_status"),
                ),
                name="order_status_change_is_real",
            ),
        ]

        indexes = [
            models.Index(
                fields=["order", "created_at"],
                name="order_history_time_idx",
            ),
            models.Index(
                fields=["to_status", "created_at"],
                name="order_history_status_idx",
            ),
        ]

    def __str__(self):
        return (
            f"{self.order.order_number}: "
            f"{self.get_from_status_display()} → "
            f"{self.get_to_status_display()}"
        )
