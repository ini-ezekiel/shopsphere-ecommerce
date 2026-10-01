from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import (
    MaxValueValidator,
    MinValueValidator,
)
from django.db import models
from django.db.models import Q

from orders.models import Order, OrderItem
from products.models import Product


class Review(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="reviews",
    )

    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name="reviews",
    )

    order_item = models.OneToOneField(
        OrderItem,
        on_delete=models.CASCADE,
        related_name="review",
    )

    rating = models.PositiveSmallIntegerField(
        validators=[
            MinValueValidator(1),
            MaxValueValidator(5),
        ],
    )

    title = models.CharField(
        max_length=150,
        blank=True,
    )

    comment = models.TextField(
        max_length=2000,
    )

    is_visible = models.BooleanField(
        default=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        ordering = [
            "-created_at",
        ]

        constraints = [
            models.UniqueConstraint(
                fields=[
                    "user",
                    "product",
                ],
                name="unique_review_per_user_product",
            ),
            models.CheckConstraint(
                condition=Q(
                    rating__gte=1,
                    rating__lte=5,
                ),
                name="review_rating_between_1_and_5",
            ),
        ]

        indexes = [
            models.Index(
                fields=[
                    "product",
                    "is_visible",
                    "-created_at",
                ],
                name="review_product_visible_idx",
            ),
            models.Index(
                fields=[
                    "user",
                    "-created_at",
                ],
                name="review_user_created_idx",
            ),
        ]

    def clean(self):
        errors = {}

        if not self.user_id or not self.product_id:
            return

        if not self.order_item_id:
            errors["order_item"] = "A delivered order item is required."

        else:
            order_item = self.order_item
            order = order_item.order

            if order.user_id != self.user_id:
                errors["order_item"] = (
                    "The selected order item does not belong " "to this customer."
                )

            if order.status != Order.Status.DELIVERED:
                errors["order_item"] = (
                    "Only products from delivered orders " "can be reviewed."
                )

            if order_item.variant_id is None:
                errors["order_item"] = (
                    "The purchased product can no longer " "be verified."
                )

            elif order_item.variant.product_id != self.product_id:
                errors["product"] = (
                    "The selected product does not match " "the purchased order item."
                )

        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        self.full_clean()

        return super().save(
            *args,
            **kwargs,
        )

    def __str__(self):
        return f"{self.user.email} — " f"{self.product.name} — " f"{self.rating}/5"
