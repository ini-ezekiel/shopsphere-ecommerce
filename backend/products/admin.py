from django.contrib import admin

from .models import (
    Brand,
    Category,
    Inventory,
    Product,
    ProductImage,
    ProductVariant,
)


class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 1
    fields = (
        "image",
        "alt_text",
        "is_primary",
        "position",
    )


class ProductVariantInline(admin.TabularInline):
    model = ProductVariant
    extra = 1
    fields = (
        "name",
        "sku",
        "attributes",
        "price",
        "discount_price",
        "is_active",
    )


class InventoryInline(admin.StackedInline):
    model = Inventory
    extra = 1
    max_num = 1
    fields = (
        "quantity",
        "reserved_quantity",
    )


@admin.register(Brand)
class BrandAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "slug",
        "is_active",
    )
    list_filter = ("is_active",)
    search_fields = ("name",)
    prepopulated_fields = {"slug": ("name",)}


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "slug",
        "is_active",
        "created_at",
    )
    list_filter = ("is_active",)
    search_fields = ("name",)
    prepopulated_fields = {"slug": ("name",)}
    readonly_fields = ("created_at", "updated_at")


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "category",
        "brand",
        "is_active",
    )
    list_filter = (
        "is_active",
        "category",
        "brand",
    )
    search_fields = (
        "name",
        "description",
    )
    prepopulated_fields = {"slug": ("name",)}
    readonly_fields = ("created_at", "updated_at")
    inlines = [
        ProductVariantInline,
        ProductImageInline,
    ]


@admin.register(ProductVariant)
class ProductVariantAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "product",
        "sku",
        "price",
        "discount_price",
        "is_active",
    )
    list_filter = (
        "is_active",
        "product__category",
        "product__brand",
    )
    search_fields = (
        "name",
        "sku",
        "product__name",
    )
    readonly_fields = ("created_at", "updated_at")
    inlines = [InventoryInline]


@admin.register(Inventory)
class InventoryAdmin(admin.ModelAdmin):
    list_display = (
        "variant",
        "quantity",
        "reserved_quantity",
        "available_quantity",
        "updated_at",
    )
    search_fields = (
        "variant__sku",
        "variant__product__name",
    )
    readonly_fields = ("updated_at",)


@admin.register(ProductImage)
class ProductImageAdmin(admin.ModelAdmin):
    list_display = (
        "product",
        "is_primary",
        "position",
        "created_at",
    )
    list_filter = ("is_primary",)
    search_fields = (
        "product__name",
        "alt_text",
    )
    readonly_fields = ("created_at",)