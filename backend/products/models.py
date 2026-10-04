from django.core.exceptions import ValidationError
from django.core.validators import FileExtensionValidator, MinValueValidator
from django.db import models
from django.db.models import F, Q
from PIL import Image, UnidentifiedImageError



def validate_image_size(image):
    if not image:
        return

    if getattr(image, "_committed", False):
        return

    max_size = 5 * 1024 * 1024

    if image.size > max_size:
        raise ValidationError("Image size must not exceed 5 MB.")


def validate_image_content(image):
    allowed_formats = {"JPEG", "PNG", "WEBP"}

    try:
        image.seek(0)

        with Image.open(image) as opened_image:
            image_format = opened_image.format
            width, height = opened_image.size

            if image_format not in allowed_formats:
                raise ValidationError("Only JPEG, PNG, and WebP images are allowed.")

            if width < 300 or height < 300:
                raise ValidationError(
                    "Image dimensions must be at least 300 × 300 pixels."
                )

            if width * height > 20_000_000:
                raise ValidationError("Image contains too many pixels.")

            opened_image.verify()

    except (
        UnidentifiedImageError,
        Image.DecompressionBombError,
        OSError,
        SyntaxError,
    ) as error:
        raise ValidationError("Upload a valid, non-corrupted image.") from error

    finally:
        try:
            image.seek(0)
        except (AttributeError, OSError):
            pass


class Brand(models.Model):
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=120, unique=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=120, unique=True)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = "categories"
        ordering = ["name"]

    def __str__(self):
        return self.name


class Product(models.Model):
    category = models.ForeignKey(
        Category,
        on_delete=models.PROTECT,
        related_name="products",
    )
    brand = models.ForeignKey(
        Brand,
        on_delete=models.PROTECT,
        related_name="products",
        null=True,
        blank=True,
    )
    name = models.CharField(max_length=200)
    slug = models.SlugField(max_length=220, unique=True)
    description = models.TextField()
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(
                fields=["category", "is_active"],
            ),
            models.Index(fields=["name"]),
        ]

    @property
    def is_in_stock(self):
        return (
            self.is_active
            and self.variants.filter(
                is_active=True,
                inventory__quantity__gt=F("inventory__reserved_quantity"),
            ).exists()
        )

    def __str__(self):
        return self.name


class ProductVariant(models.Model):
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name="variants",
    )
    name = models.CharField(max_length=150)
    sku = models.CharField(max_length=50, unique=True)
    attributes = models.JSONField(default=dict, blank=True)
    price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(0)],
    )
    discount_price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        null=True,
        blank=True,
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["product", "price"]
        constraints = [
            models.UniqueConstraint(
                fields=["product", "attributes"],
                name="unique_product_variant_attributes",
            ),
            models.CheckConstraint(
                condition=Q(price__gte=0),
                name="variant_price_non_negative",
            ),
            models.CheckConstraint(
                condition=(
                    Q(discount_price__isnull=True) | Q(discount_price__lte=F("price"))
                ),
                name="variant_discount_not_above_price",
            ),
        ]

    @property
    def current_price(self):
        return self.discount_price if self.discount_price is not None else self.price

    @property
    def is_in_stock(self):
        inventory = getattr(self, "inventory", None)

        return (
            self.is_active
            and self.product.is_active
            and inventory is not None
            and inventory.available_quantity > 0
        )

    def __str__(self):
        return f"{self.product.name} — {self.name}"


class Inventory(models.Model):
    variant = models.OneToOneField(
        ProductVariant,
        on_delete=models.CASCADE,
        related_name="inventory",
    )
    quantity = models.PositiveIntegerField(default=0)
    reserved_quantity = models.PositiveIntegerField(default=0)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = "inventory"
        constraints = [
            models.CheckConstraint(
                condition=Q(quantity__gte=0),
                name="inventory_quantity_non_negative",
            ),
            models.CheckConstraint(
                condition=Q(reserved_quantity__gte=0),
                name="inventory_reserved_non_negative",
            ),
            models.CheckConstraint(
                condition=Q(reserved_quantity__lte=F("quantity")),
                name="inventory_reserved_not_above_quantity",
            ),
        ]

    @property
    def available_quantity(self):
        return self.quantity - self.reserved_quantity

    def __str__(self):
        return f"Inventory for {self.variant.sku}"


class ProductImage(models.Model):
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name="images",
    )
    image = models.ImageField(
        upload_to="products/%Y/%m/",
        validators=[
            FileExtensionValidator(
                allowed_extensions=[
                    "jpg",
                    "jpeg",
                    "png",
                    "webp",
                ]
            ),
            validate_image_size,
            validate_image_content,
        ],
    )

    alt_text = models.CharField(max_length=255, blank=True)
    is_primary = models.BooleanField(default=False)
    position = models.PositiveSmallIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["position", "created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["product"],
                condition=Q(is_primary=True),
                name="one_primary_image_per_product",
            ),
        ]

    def __str__(self):
        return f"Image for {self.product.name}"
