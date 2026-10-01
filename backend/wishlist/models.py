from django.conf import settings
from django.db import models

from products.models import Product


class WishlistItem(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="wishlist_items",
    )

    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name="wishlist_items",
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    class Meta:
        ordering = ["-created_at"]

        constraints = [
            models.UniqueConstraint(
                fields=[
                    "user",
                    "product",
                ],
                name="unique_product_per_user_wishlist",
            ),
        ]

        indexes = [
            models.Index(
                fields=[
                    "user",
                    "created_at",
                ],
                name="wishlist_user_created_idx",
            ),
        ]

    def __str__(self):
        return f"{self.user.email} — " f"{self.product.name}"