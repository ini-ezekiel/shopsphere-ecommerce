from django.db import transaction

from orders.models import Order, OrderItem

from .models import Review


class ReviewError(Exception):
    def __init__(self, message):
        self.message = message
        super().__init__(message)


@transaction.atomic
def create_verified_review(
    *,
    user,
    product,
    rating,
    title,
    comment,
):
    if not user.is_authenticated:
        raise ReviewError("Authentication is required.")

    if not user.is_email_verified:
        raise ReviewError("Verify your email address before reviewing products.")

    if not product.is_active:
        raise ReviewError("This product is unavailable.")

    if Review.objects.filter(
        user=user,
        product=product,
    ).exists():
        raise ReviewError("You have already reviewed this product.")

    order_item = (
        OrderItem.objects.select_for_update(
            of=("self",),
        )
        .select_related(
            "order",
            "variant__product",
        )
        .filter(
            order__user=user,
            order__status=Order.Status.DELIVERED,
            order__inventory_status=(Order.InventoryStatus.COMMITTED),
            variant__product=product,
            review__isnull=True,
        )
        .order_by(
            "-order__updated_at",
            "-id",
        )
        .first()
    )

    if order_item is None:
        raise ReviewError(
            "Only customers with a delivered purchase " "can review this product."
        )

    # Check again after locking the qualifying order item.
    if Review.objects.filter(
        user=user,
        product=product,
    ).exists():
        raise ReviewError("You have already reviewed this product.")

    review = Review.objects.create(
        user=user,
        product=product,
        order_item=order_item,
        rating=rating,
        title=title,
        comment=comment,
    )

    return review
