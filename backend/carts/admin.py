from django.contrib import admin

from .models import Cart, CartItem


class CartItemInline(admin.TabularInline):
    model = CartItem
    extra = 0
    readonly_fields = [
        "unit_price_display",
        "subtotal_display",
        "created_at",
        "updated_at",
    ]

    @admin.display(description="Unit price")
    def unit_price_display(self, obj):
        if obj.pk:
            return obj.unit_price

        return None

    @admin.display(description="Subtotal")
    def subtotal_display(self, obj):
        if obj.pk:
            return obj.subtotal

        return None


@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "user",
        "total_quantity_display",
        "total_display",
        "updated_at",
    ]
    search_fields = [
        "user__email",
        "user__username",
    ]
    readonly_fields = [
        "created_at",
        "updated_at",
        "total_quantity_display",
        "total_display",
    ]
    inlines = [CartItemInline]

    @admin.display(description="Total quantity")
    def total_quantity_display(self, obj):
        return obj.total_quantity

    @admin.display(description="Total")
    def total_display(self, obj):
        return obj.total


@admin.register(CartItem)
class CartItemAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "cart",
        "variant",
        "quantity",
        "unit_price_display",
        "subtotal_display",
        "updated_at",
    ]
    search_fields = [
        "cart__user__email",
        "variant__sku",
        "variant__product__name",
    ]
    list_select_related = [
        "cart__user",
        "variant__product",
    ]

    @admin.display(description="Unit price")
    def unit_price_display(self, obj):
        return obj.unit_price

    @admin.display(description="Subtotal")
    def subtotal_display(self, obj):
        return obj.subtotal
