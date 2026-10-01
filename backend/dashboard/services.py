from datetime import datetime, time, timedelta
from decimal import Decimal

from django.conf import settings
from django.contrib.auth import get_user_model
from django.db.models import (
    Count,
    DecimalField,
    ExpressionWrapper,
    F,
    IntegerField,
    Q,
    Sum,
)
from django.db.models.functions import Coalesce
from django.utils import timezone

from orders.models import Order
from payments.models import Payment, Refund
from products.models import (
    Inventory,
    Product,
    ProductVariant,
)

User = get_user_model()

MONEY_OUTPUT_FIELD = DecimalField(
    max_digits=18,
    decimal_places=2,
)


def get_period_start(period):
    current_time = timezone.now()

    if period == "today":
        current_date = timezone.localdate()

        return timezone.make_aware(
            datetime.combine(
                current_date,
                time.min,
            ),
            timezone.get_current_timezone(),
        )

    if period == "7d":
        return current_time - timedelta(days=7)

    if period == "30d":
        return current_time - timedelta(days=30)

    return None


def sum_money(queryset, field_name):
    result = queryset.aggregate(
        total=Coalesce(
            Sum(field_name),
            Decimal("0.00"),
            output_field=MONEY_OUTPUT_FIELD,
        )
    )

    return result["total"]


def build_order_summary(queryset):
    status_counts = {
        row["status"]: row["count"]
        for row in queryset.values("status").annotate(
            count=Count("id"),
        )
    }

    return {
        "total": queryset.count(),
        "pending_payment": status_counts.get(
            Order.Status.PENDING_PAYMENT,
            0,
        ),
        "confirmed": status_counts.get(
            Order.Status.CONFIRMED,
            0,
        ),
        "processing": status_counts.get(
            Order.Status.PROCESSING,
            0,
        ),
        "shipped": status_counts.get(
            Order.Status.SHIPPED,
            0,
        ),
        "delivered": status_counts.get(
            Order.Status.DELIVERED,
            0,
        ),
        "cancelled": status_counts.get(
            Order.Status.CANCELLED,
            0,
        ),
    }


def build_catalog_summary():
    low_stock_threshold = getattr(
        settings,
        "DASHBOARD_LOW_STOCK_THRESHOLD",
        5,
    )

    active_product_filter = (
        Q(is_active=True)
        & Q(category__is_active=True)
        & (Q(brand__isnull=True) | Q(brand__is_active=True))
    )

    active_variant_filter = (
        Q(is_active=True)
        & Q(product__is_active=True)
        & Q(product__category__is_active=True)
        & (Q(product__brand__isnull=True) | Q(product__brand__is_active=True))
    )

    inventory_queryset = (
        Inventory.objects.filter(
            variant__is_active=True,
            variant__product__is_active=True,
            variant__product__category__is_active=True,
        )
        .filter(
            Q(variant__product__brand__isnull=True)
            | Q(variant__product__brand__is_active=True)
        )
        .annotate(
            available_quantity_value=ExpressionWrapper(
                F("quantity") - F("reserved_quantity"),
                output_field=IntegerField(),
            )
        )
    )

    return {
        "active_products": Product.objects.filter(
            active_product_filter,
        ).count(),
        "active_variants": ProductVariant.objects.filter(
            active_variant_filter,
        ).count(),
        "low_stock_variants": inventory_queryset.filter(
            available_quantity_value__gt=0,
            available_quantity_value__lte=(low_stock_threshold),
        ).count(),
        "out_of_stock_variants": inventory_queryset.filter(
            available_quantity_value__lte=0,
        ).count(),
    }


def build_recent_orders(queryset):
    orders = queryset.select_related(
        "user",
    ).order_by(
        "-created_at",
    )[:5]

    return [
        {
            "order_number": order.order_number,
            "customer_email": order.user.email,
            "status": order.status,
            "status_display": (order.get_status_display()),
            "total_amount": order.total_amount,
            "created_at": order.created_at,
        }
        for order in orders
    ]


def build_recent_refunds(queryset):
    refunds = queryset.select_related(
        "payment",
        "payment__order",
    ).order_by(
        "-created_at",
    )[:5]

    return [
        {
            "reference": refund.reference,
            "order_number": (refund.payment.order.order_number),
            "status": refund.status,
            "status_display": (refund.get_status_display()),
            "amount": refund.amount,
            "created_at": refund.created_at,
        }
        for refund in refunds
    ]


def build_dashboard_summary(period):
    generated_at = timezone.now()
    period_start = get_period_start(period)

    order_queryset = Order.objects.all()
    payment_queryset = Payment.objects.filter(
        status__in=[
            Payment.Status.SUCCESSFUL,
            Payment.Status.REFUNDED,
        ],
        paid_at__isnull=False,
    )
    processed_refund_queryset = Refund.objects.filter(
        status=Refund.Status.PROCESSED,
    )
    recent_refund_queryset = Refund.objects.all()

    if period_start is not None:
        order_queryset = order_queryset.filter(
            created_at__gte=period_start,
        )

        payment_queryset = payment_queryset.filter(
            paid_at__gte=period_start,
        )

        processed_refund_queryset = processed_refund_queryset.filter(
            processed_at__gte=period_start,
        )

        recent_refund_queryset = recent_refund_queryset.filter(
            created_at__gte=period_start,
        )

    gross_paid_amount = sum_money(
        payment_queryset,
        "amount",
    )

    processed_refund_amount = sum_money(
        processed_refund_queryset,
        "amount",
    )

    net_sales = gross_paid_amount - processed_refund_amount

    customer_queryset = User.objects.filter(
        is_staff=False,
    )

    if period_start is None:
        new_customers = customer_queryset.count()
    else:
        new_customers = customer_queryset.filter(
            date_joined__gte=period_start,
        ).count()

    return {
        "period": period,
        "period_start": period_start,
        "generated_at": generated_at,
        "financial": {
            "currency": "NGN",
            "gross_paid_amount": gross_paid_amount,
            "processed_refund_amount": (processed_refund_amount),
            "net_sales": net_sales,
        },
        "orders": build_order_summary(
            order_queryset,
        ),
        "catalog": build_catalog_summary(),
        "customers": {
            "total_customers": (customer_queryset.count()),
            "new_customers": new_customers,
        },
        "recent_orders": build_recent_orders(
            order_queryset,
        ),
        "recent_refunds": build_recent_refunds(
            recent_refund_queryset,
        ),
    }
