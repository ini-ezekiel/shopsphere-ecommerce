"""
These serializers control how cart data is returned and prevent
users from adding unavailable quantities.
"""

from django.db import transaction
from rest_framework import serializers

from products.models import ProductVariant

from .models import Cart, CartItem

# returns the selected size, colour, price, stock and primary image


class CartVariantSerializer(serializers.ModelSerializer):
    product_id = serializers.IntegerField(
        source="product.id",
        read_only=True,
    )
    product_name = serializers.CharField(
        source="product.name",
        read_only=True,
    )
    product_slug = serializers.CharField(
        source="product.slug",
        read_only=True,
    )
    current_price = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
        read_only=True,
    )
    available_quantity = serializers.SerializerMethodField()
    primary_image = serializers.SerializerMethodField()

    class Meta:
        model = ProductVariant
        fields = [
            "id",
            "product_id",
            "product_name",
            "product_slug",
            "name",
            "sku",
            "attributes",
            "price",
            "discount_price",
            "current_price",
            "available_quantity",
            "primary_image",
        ]

    def get_available_quantity(self, obj):
        inventory = getattr(obj, "inventory", None)

        if inventory is None:
            return 0

        return inventory.available_quantity

    def get_primary_image(self, obj):
        image = obj.product.images.filter(
            is_primary=True,
        ).first()

        if image is None:
            return None

        request = self.context.get("request")
        image_url = image.image.url

        if request:
            return request.build_absolute_uri(image_url)

        return image_url


# This serializer returns each cart row and its subtotal


class CartItemSerializer(serializers.ModelSerializer):
    variant = CartVariantSerializer(read_only=True)
    unit_price = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
        read_only=True,
    )
    subtotal = serializers.DecimalField(
        max_digits=14,
        decimal_places=2,
        read_only=True,
    )

    class Meta:
        model = CartItem
        fields = [
            "id",
            "variant",
            "quantity",
            "unit_price",
            "subtotal",
            "created_at",
            "updated_at",
        ]


# Cart serializer returns the complete cart and totals.


class CartSerializer(serializers.ModelSerializer):
    items = CartItemSerializer(
        many=True,
        read_only=True,
    )
    total_quantity = serializers.IntegerField(
        read_only=True,
    )
    total = serializers.DecimalField(
        max_digits=14,
        decimal_places=2,
        read_only=True,
    )

    class Meta:
        model = Cart
        fields = [
            "id",
            "items",
            "total_quantity",
            "total",
            "created_at",
            "updated_at",
        ]


# adding a new variant or increasing its existing quantity


class AddCartItemSerializer(serializers.Serializer):
    variant_id = serializers.PrimaryKeyRelatedField(
        source="variant",
        queryset=ProductVariant.objects.select_related(
            "product",
            "inventory",
        ),
    )
    quantity = serializers.IntegerField(
        min_value=1,
        max_value=99,
        default=1,
    )

    def validate(self, attrs):
        variant = attrs["variant"]
        quantity = attrs["quantity"]
        cart = self.context["cart"]

        if not variant.is_active or not variant.product.is_active:
            raise serializers.ValidationError(
                {"variant_id": ("This product variant is unavailable.")}
            )

        inventory = getattr(variant, "inventory", None)

        if inventory is None:
            raise serializers.ValidationError(
                {"variant_id": ("Inventory is unavailable for this variant.")}
            )

        existing_quantity = (
            CartItem.objects.filter(
                cart=cart,
                variant=variant,
            )
            .values_list("quantity", flat=True)
            .first()
            or 0
        )

        requested_total = existing_quantity + quantity

        if requested_total > inventory.available_quantity:
            raise serializers.ValidationError(
                {"quantity": ("The requested quantity exceeds " "available inventory.")}
            )

        return attrs

    def create(self, validated_data):
        variant = validated_data["variant"]
        quantity = validated_data["quantity"]

        with transaction.atomic():
            cart = Cart.objects.select_for_update().get(pk=self.context["cart"].pk)

            variant = ProductVariant.objects.select_related(
                "product",
                "inventory",
            ).get(pk=variant.pk)

            inventory = getattr(
                variant,
                "inventory",
                None,
            )

            item = (
                CartItem.objects.select_for_update()
                .filter(
                    cart=cart,
                    variant=variant,
                )
                .first()
            )

            new_quantity = quantity

            if item:
                new_quantity += item.quantity

            if inventory is None or new_quantity > inventory.available_quantity:
                raise serializers.ValidationError(
                    {
                        "quantity": (
                            "The requested quantity exceeds " "available inventory."
                        )
                    }
                )

            if item:
                self.created = False
                item.quantity = new_quantity
                item.save(update_fields=["quantity", "updated_at"])

            else:
                self.created = True
                item = CartItem.objects.create(
                    cart=cart,
                    variant=variant,
                    quantity=quantity,
                )

        return item


# UpdateCartItemSerializer replaces the quantity of an existing item.


class UpdateCartItemSerializer(serializers.Serializer):
    quantity = serializers.IntegerField(
        min_value=1,
        max_value=99,
    )

    def update(self, instance, validated_data):
        with transaction.atomic():
            item = CartItem.objects.select_for_update().get(pk=instance.pk)

            variant = ProductVariant.objects.select_related(
                "product",
                "inventory",
            ).get(pk=item.variant_id)

            inventory = getattr(
                variant,
                "inventory",
                None,
            )
            quantity = validated_data["quantity"]

            if (
                not variant.is_active
                or not variant.product.is_active
                or inventory is None
            ):
                raise serializers.ValidationError(
                    {"quantity": ("This product variant " "is unavailable.")}
                )

            if quantity > inventory.available_quantity:
                raise serializers.ValidationError(
                    {
                        "quantity": (
                            "The requested quantity exceeds " "available inventory."
                        )
                    }
                )

            item.quantity = quantity
            item.save(
                update_fields=[
                    "quantity",
                    "updated_at",
                ]
            )

        return item
