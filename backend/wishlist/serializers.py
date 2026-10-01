from django.db.models import Q
from rest_framework import serializers

from products.models import Product
from products.serializers import ProductImageSerializer

from .models import WishlistItem


class WishlistProductSerializer(serializers.ModelSerializer):
    primary_image = serializers.SerializerMethodField()
    starting_price = serializers.SerializerMethodField()
    is_in_stock = serializers.SerializerMethodField()
    is_available = serializers.SerializerMethodField()

    class Meta:
        model = Product

        fields = [
            "id",
            "name",
            "slug",
            "starting_price",
            "is_in_stock",
            "is_available",
            "primary_image",
        ]

        read_only_fields = fields

    def get_variants(self, product):
        prefetched_variants = getattr(
            product,
            "active_wishlist_variants",
            None,
        )

        if prefetched_variants is not None:
            return prefetched_variants

        return list(
            product.variants.filter(
                is_active=True,
            ).select_related("inventory")
        )

    def get_primary_image(self, product):
        images = list(product.images.all())

        primary_image = next(
            (image for image in images if image.is_primary),
            None,
        )

        if primary_image is None:
            return None

        return ProductImageSerializer(
            primary_image,
            context=self.context,
        ).data

    def get_starting_price(self, product):
        variants = self.get_variants(product)

        prices = [variant.current_price for variant in variants]

        if not prices:
            return None

        return f"{min(prices):.2f}"

    def get_is_in_stock(self, product):
        variants = self.get_variants(product)

        return any(variant.is_in_stock for variant in variants)

    def get_is_available(self, product):
        if not product.is_active:
            return False

        if not product.category.is_active:
            return False

        if product.brand is not None and not product.brand.is_active:
            return False

        return True


class WishlistItemSerializer(serializers.ModelSerializer):
    product = WishlistProductSerializer(
        read_only=True,
    )

    product_id = serializers.PrimaryKeyRelatedField(
        source="product",
        queryset=Product.objects.filter(
            is_active=True,
            category__is_active=True,
        ).filter(Q(brand__isnull=True) | Q(brand__is_active=True)),
        write_only=True,
        error_messages={
            "does_not_exist": ("The selected product is unavailable."),
            "incorrect_type": ("The product ID must be an integer."),
        },
    )

    class Meta:
        model = WishlistItem

        fields = [
            "id",
            "product_id",
            "product",
            "created_at",
        ]

        read_only_fields = [
            "id",
            "product",
            "created_at",
        ]

    def create(self, validated_data):
        request = self.context["request"]

        wishlist_item, created = WishlistItem.objects.get_or_create(
            user=request.user,
            product=validated_data["product"],
        )

        self.created = created

        return wishlist_item
