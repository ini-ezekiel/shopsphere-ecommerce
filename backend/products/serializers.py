from rest_framework import serializers

from .models import (
    Brand,
    Category,
    Inventory,
    Product,
    ProductImage,
    ProductVariant,
)


class BrandSerializer(serializers.ModelSerializer):
    class Meta:
        model = Brand

        fields = (
            "id",
            "name",
            "slug",
        )


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category

        fields = (
            "id",
            "name",
            "slug",
            "description",
        )


class ProductImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductImage

        fields = (
            "id",
            "image",
            "alt_text",
            "is_primary",
            "position",
        )


class StaffProductImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductImage

        fields = [
            "id",
            "image",
            "alt_text",
            "is_primary",
            "position",
            "created_at",
        ]

        read_only_fields = [
            "id",
            "created_at",
        ]


class ProductVariantSerializer(serializers.ModelSerializer):
    current_price = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
        read_only=True,
    )

    is_in_stock = serializers.BooleanField(
        read_only=True,
    )

    class Meta:
        model = ProductVariant

        fields = (
            "id",
            "name",
            "sku",
            "attributes",
            "price",
            "discount_price",
            "current_price",
            "is_in_stock",
        )


class ProductListSerializer(serializers.ModelSerializer):
    category = CategorySerializer(
        read_only=True,
    )

    brand = BrandSerializer(
        read_only=True,
    )

    primary_image = serializers.SerializerMethodField()
    starting_price = serializers.SerializerMethodField()
    is_in_stock = serializers.SerializerMethodField()

    average_rating = serializers.DecimalField(
        max_digits=3,
        decimal_places=2,
        read_only=True,
        allow_null=True,
    )

    review_count = serializers.IntegerField(
        read_only=True,
    )

    class Meta:
        model = Product

        fields = (
            "id",
            "name",
            "slug",
            "category",
            "brand",
            "starting_price",
            "is_in_stock",
            "average_rating",
            "review_count",
            "primary_image",
        )

    def get_primary_image(self, product):
        primary_image = next(
            (image for image in product.images.all() if image.is_primary),
            None,
        )

        if primary_image is None:
            return None

        return ProductImageSerializer(
            primary_image,
            context=self.context,
        ).data

    def get_starting_price(self, product):
        variants = getattr(
            product,
            "active_variants",
            [],
        )

        prices = [variant.current_price for variant in variants]

        if not prices:
            return None

        return f"{min(prices):.2f}"

    def get_is_in_stock(self, product):
        variants = getattr(
            product,
            "active_variants",
            [],
        )

        return any(variant.is_in_stock for variant in variants)


class ProductDetailSerializer(serializers.ModelSerializer):
    category = CategorySerializer(
        read_only=True,
    )

    brand = BrandSerializer(
        read_only=True,
    )

    images = ProductImageSerializer(
        many=True,
        read_only=True,
    )

    variants = ProductVariantSerializer(
        source="active_variants",
        many=True,
        read_only=True,
    )

    is_in_stock = serializers.SerializerMethodField()

    average_rating = serializers.DecimalField(
        max_digits=3,
        decimal_places=2,
        read_only=True,
        allow_null=True,
    )

    review_count = serializers.IntegerField(
        read_only=True,
    )

    class Meta:
        model = Product

        fields = (
            "id",
            "name",
            "slug",
            "description",
            "category",
            "brand",
            "is_in_stock",
            "average_rating",
            "review_count",
            "images",
            "variants",
            "created_at",
            "updated_at",
        )

    def get_is_in_stock(self, product):
        return any(variant.is_in_stock for variant in product.active_variants)


class StaffBrandSerializer(serializers.ModelSerializer):
    class Meta:
        model = Brand

        fields = [
            "id",
            "name",
            "slug",
            "is_active",
        ]

        read_only_fields = [
            "id",
        ]


class StaffCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category

        fields = [
            "id",
            "name",
            "slug",
            "description",
            "is_active",
            "created_at",
            "updated_at",
        ]

        read_only_fields = [
            "id",
            "created_at",
            "updated_at",
        ]


class StaffVariantInventorySerializer(serializers.ModelSerializer):
    available_quantity = serializers.IntegerField(
        read_only=True,
    )

    class Meta:
        model = Inventory

        fields = [
            "id",
            "quantity",
            "reserved_quantity",
            "available_quantity",
            "updated_at",
        ]

        read_only_fields = fields


class StaffProductVariantSerializer(serializers.ModelSerializer):
    current_price = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
        read_only=True,
    )

    is_in_stock = serializers.BooleanField(
        read_only=True,
    )

    inventory = serializers.SerializerMethodField()

    def get_inventory(self, variant):
        inventory = getattr(
            variant,
            "inventory",
            None,
        )

        if inventory is None:
            return None

        return StaffVariantInventorySerializer(
            inventory,
            context=self.context,
        ).data

    class Meta:
        model = ProductVariant

        fields = [
            "id",
            "name",
            "sku",
            "attributes",
            "price",
            "discount_price",
            "current_price",
            "is_active",
            "is_in_stock",
            "inventory",
            "created_at",
            "updated_at",
        ]

        read_only_fields = fields


class StaffProductSerializer(serializers.ModelSerializer):
    category = StaffCategorySerializer(
        read_only=True,
    )

    brand = StaffBrandSerializer(
        read_only=True,
    )

    images = ProductImageSerializer(
        many=True,
        read_only=True,
    )

    variants = StaffProductVariantSerializer(
        many=True,
        read_only=True,
    )

    starting_price = serializers.SerializerMethodField()
    is_in_stock = serializers.BooleanField(
        read_only=True,
    )

    variant_count = serializers.SerializerMethodField()

    def get_starting_price(self, product):
        prices = [
            variant.current_price
            for variant in product.variants.all()
            if variant.is_active
        ]

        if not prices:
            return None

        return f"{min(prices):.2f}"

    def get_variant_count(self, product):
        return len(product.variants.all())

    class Meta:
        model = Product

        fields = [
            "id",
            "name",
            "slug",
            "description",
            "category",
            "brand",
            "is_active",
            "is_in_stock",
            "starting_price",
            "variant_count",
            "images",
            "variants",
            "created_at",
            "updated_at",
        ]

        read_only_fields = fields


class StaffProductWriteSerializer(serializers.ModelSerializer):
    category_id = serializers.PrimaryKeyRelatedField(
        source="category",
        queryset=Category.objects.all(),
    )

    brand_id = serializers.PrimaryKeyRelatedField(
        source="brand",
        queryset=Brand.objects.all(),
        required=False,
        allow_null=True,
    )

    class Meta:
        model = Product

        fields = [
            "name",
            "slug",
            "description",
            "category_id",
            "brand_id",
            "is_active",
        ]

    def validate_name(self, value):
        value = value.strip()

        if not value:
            raise serializers.ValidationError("A product name is required.")

        return value

    def validate_description(self, value):
        value = value.strip()

        if not value:
            raise serializers.ValidationError("A product description is required.")

        return value


class StaffProductVariantWriteSerializer(serializers.ModelSerializer):
    product_id = serializers.PrimaryKeyRelatedField(
        source="product",
        queryset=Product.objects.all(),
        write_only=True,
        required=False,
    )

    initial_quantity = serializers.IntegerField(
        min_value=0,
        write_only=True,
        required=False,
        default=0,
    )

    class Meta:
        model = ProductVariant

        fields = [
            "product_id",
            "name",
            "sku",
            "attributes",
            "price",
            "discount_price",
            "is_active",
            "initial_quantity",
        ]

        validators = []

    def validate_name(self, value):
        value = value.strip()

        if not value:
            raise serializers.ValidationError("A variant name is required.")

        return value

    def validate_sku(self, value):
        value = value.strip().upper()

        if not value:
            raise serializers.ValidationError("A SKU is required.")

        duplicate_sku = ProductVariant.objects.filter(
            sku__iexact=value,
        )

        if self.instance is not None:
            duplicate_sku = duplicate_sku.exclude(
                pk=self.instance.pk,
            )

        if duplicate_sku.exists():
            raise serializers.ValidationError("A variant with this SKU already exists.")

        return value

    def validate(self, attrs):
        instance = self.instance

        product = attrs.get(
            "product",
            self.context.get(
                "product",
                getattr(instance, "product", None),
            ),
        )

        attributes = attrs.get(
            "attributes",
            getattr(instance, "attributes", {}),
        )

        price = attrs.get(
            "price",
            getattr(instance, "price", None),
        )

        discount_price = attrs.get(
            "discount_price",
            getattr(instance, "discount_price", None),
        )

        if discount_price is not None and price is not None and discount_price > price:
            raise serializers.ValidationError(
                {
                    "discount_price": (
                        "The discount price cannot be "
                        "greater than the regular price."
                    )
                }
            )

        if product is not None:
            duplicate_variant = ProductVariant.objects.filter(
                product=product,
                attributes=attributes,
            )

            if instance is not None:
                duplicate_variant = duplicate_variant.exclude(
                    pk=instance.pk,
                )

            if duplicate_variant.exists():
                raise serializers.ValidationError(
                    {
                        "attributes": (
                            "A variant with these attributes "
                            "already exists for this product."
                        )
                    }
                )

        if instance is not None:
            attrs.pop(
                "product",
                None,
            )

            attrs.pop(
                "initial_quantity",
                None,
            )

        return attrs


class StaffInventorySerializer(serializers.ModelSerializer):
    variant_id = serializers.IntegerField(
        read_only=True,
    )

    sku = serializers.CharField(
        source="variant.sku",
        read_only=True,
    )

    product_name = serializers.CharField(
        source="variant.product.name",
        read_only=True,
    )

    variant_name = serializers.CharField(
        source="variant.name",
        read_only=True,
    )

    available_quantity = serializers.IntegerField(
        read_only=True,
    )

    class Meta:
        model = Inventory

        fields = [
            "id",
            "variant_id",
            "sku",
            "product_name",
            "variant_name",
            "quantity",
            "reserved_quantity",
            "available_quantity",
            "updated_at",
        ]

        read_only_fields = fields


class StaffInventoryUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Inventory

        fields = [
            "quantity",
        ]

    def validate_quantity(self, value):
        if self.instance is not None and value < self.instance.reserved_quantity:
            raise serializers.ValidationError(
                "Inventory quantity cannot be lower than "
                "the currently reserved quantity."
            )

        return value
