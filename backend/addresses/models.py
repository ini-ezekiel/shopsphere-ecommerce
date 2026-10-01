from django.conf import settings
from django.core.validators import MinValueValidator, RegexValidator
from django.db import models
from django.db.models import Q
from django.db.models.functions import Lower

phone_validator = RegexValidator(
    regex=r"^(?:\+234|0)[789]\d{9}$",
    message=(
        "Enter a valid Nigerian phone number, "
        "for example 08012345678 or +2348012345678."
    ),
)


class DeliveryLocation(models.Model):
    state = models.CharField(max_length=100)
    city = models.CharField(max_length=100)

    shipping_fee = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(0)],
    )

    estimated_delivery_days = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1)],
    )

    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["state", "city"]

        constraints = [
            models.UniqueConstraint(
                Lower("state"),
                Lower("city"),
                name="unique_delivery_state_city_case_insensitive",
            ),
            models.CheckConstraint(
                condition=Q(shipping_fee__gte=0),
                name="delivery_shipping_fee_non_negative",
            ),
            models.CheckConstraint(
                condition=Q(estimated_delivery_days__gte=1),
                name="delivery_days_at_least_one",
            ),
        ]

        indexes = [
            models.Index(
                fields=["state", "is_active"],
                name="delivery_state_active_idx",
            ),
        ]

    def __str__(self):
        return f"{self.city}, {self.state}"


class ShippingAddress(models.Model):
    class Label(models.TextChoices):
        HOME = "home", "Home"
        WORK = "work", "Work"
        OTHER = "other", "Other"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="shipping_addresses",
    )

    delivery_location = models.ForeignKey(
        DeliveryLocation,
        on_delete=models.PROTECT,
        related_name="shipping_addresses",
    )

    label = models.CharField(
        max_length=20,
        choices=Label.choices,
        default=Label.HOME,
    )

    recipient_name = models.CharField(max_length=150)

    phone_number = models.CharField(
        max_length=20,
        validators=[phone_validator],
    )

    address_line_1 = models.CharField(max_length=255)
    address_line_2 = models.CharField(max_length=255, blank=True)
    landmark = models.CharField(max_length=255, blank=True)
    postal_code = models.CharField(max_length=20, blank=True)

    country = models.CharField(
        max_length=100,
        default="Nigeria",
        editable=False,
    )

    is_default = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-is_default", "-updated_at"]

        constraints = [
            models.UniqueConstraint(
                fields=["user"],
                condition=Q(is_default=True),
                name="one_default_shipping_address_per_user",
            ),
        ]

        indexes = [
            models.Index(
                fields=["user", "is_default"],
                name="shipping_user_default_idx",
            ),
        ]

    def __str__(self):
        return (
            f"{self.recipient_name} — "
            f"{self.delivery_location.city}, "
            f"{self.delivery_location.state}"
        )
