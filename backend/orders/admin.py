from django.contrib import admin

from .models import (
    Order,
    OrderItem,
    OrderStatusHistory,
)


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    can_delete = False
    show_change_link = False

    fields = [
        "product_name",
        "variant_name",
        "sku",
        "attributes",
        "unit_price",
        "quantity",
        "line_total",
    ]

    readonly_fields = fields

    def has_add_permission(self, request, obj=None):
        return False


class OrderStatusHistoryInline(admin.TabularInline):
    model = OrderStatusHistory
    extra = 0
    can_delete = False
    show_change_link = False

    fields = [
        "from_status",
        "to_status",
        "changed_by_email",
        "note",
        "created_at",
    ]

    readonly_fields = fields

    ordering = [
        "created_at",
    ]

    def has_add_permission(
        self,
        request,
        obj=None,
    ):
        return False


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = [
        "order_number",
        "user",
        "status",
        "inventory_status",
        "cancellation_reason",
        "total_amount",
        "currency",
        "created_at",
    ]

    list_filter = [
        "status",
        "inventory_status",
        "cancellation_reason",
        "currency",
        "created_at",
    ]

    search_fields = [
        "order_number",
        "user__email",
        "recipient_name",
        "phone_number",
    ]

    list_select_related = [
        "user",
    ]

    date_hierarchy = "created_at"

    ordering = [
        "-created_at",
    ]

    readonly_fields = [
        "user",
        "order_number",
        "idempotency_key",
        "status",
        "inventory_status",
        "shipping_address",
        "recipient_name",
        "phone_number",
        "address_line_1",
        "address_line_2",
        "landmark",
        "postal_code",
        "city",
        "state",
        "country",
        "estimated_delivery_days",
        "currency",
        "subtotal",
        "discount_amount",
        "shipping_fee",
        "total_amount",
        "reservation_expires_at",
        "cancelled_at",
        "cancellation_reason",
        "created_at",
        "updated_at",
    ]

    fieldsets = [
        (
            "Order",
            {
                "fields": [
                    "order_number",
                    "idempotency_key",
                    "user",
                    "status",
                    "inventory_status",
                ]
            },
        ),
        (
            "Delivery address snapshot",
            {
                "fields": [
                    "shipping_address",
                    "recipient_name",
                    "phone_number",
                    "address_line_1",
                    "address_line_2",
                    "landmark",
                    "postal_code",
                    "city",
                    "state",
                    "country",
                    "estimated_delivery_days",
                ]
            },
        ),
        (
            "Financial summary",
            {
                "fields": [
                    "currency",
                    "subtotal",
                    "discount_amount",
                    "shipping_fee",
                    "total_amount",
                ]
            },
        ),
        (
            "Reservation and cancellation",
            {
                "fields": [
                    "reservation_expires_at",
                    "cancelled_at",
                    "cancellation_reason",
                ]
            },
        ),
        (
            "Timestamps",
            {
                "fields": [
                    "created_at",
                    "updated_at",
                ]
            },
        ),
    ]

    inlines = [
        OrderItemInline,
        OrderStatusHistoryInline,
    ]

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = [
        "product_name",
        "variant_name",
        "sku",
        "quantity",
        "unit_price",
        "line_total",
        "order",
    ]

    list_filter = [
        "created_at",
    ]

    search_fields = [
        "order__order_number",
        "product_name",
        "variant_name",
        "sku",
    ]

    list_select_related = [
        "order",
        "variant",
    ]

    readonly_fields = [
        "order",
        "variant",
        "product_name",
        "variant_name",
        "sku",
        "attributes",
        "unit_price",
        "quantity",
        "line_total",
        "created_at",
    ]

    ordering = [
        "-created_at",
    ]

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(OrderStatusHistory)
class OrderStatusHistoryAdmin(admin.ModelAdmin):
    list_display = [
        "order",
        "from_status",
        "to_status",
        "changed_by_email",
        "created_at",
    ]

    list_filter = [
        "from_status",
        "to_status",
        "created_at",
    ]

    search_fields = [
        "order__order_number",
        "order__user__email",
        "changed_by_email",
        "note",
    ]

    list_select_related = [
        "order",
        "order__user",
        "changed_by",
    ]

    readonly_fields = [
        "order",
        "from_status",
        "to_status",
        "changed_by",
        "changed_by_email",
        "note",
        "created_at",
    ]

    ordering = [
        "-created_at",
    ]

    date_hierarchy = "created_at"

    def has_add_permission(self, request):
        return False

    def has_delete_permission(
        self,
        request,
        obj=None,
    ):
        return False
