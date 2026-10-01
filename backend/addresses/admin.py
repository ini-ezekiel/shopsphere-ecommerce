from django.contrib import admin

from .models import DeliveryLocation, ShippingAddress


@admin.register(DeliveryLocation)
class DeliveryLocationAdmin(admin.ModelAdmin):
    list_display = [
        "city",
        "state",
        "shipping_fee",
        "estimated_delivery_days",
        "is_active",
    ]

    list_filter = [
        "state",
        "is_active",
    ]

    search_fields = [
        "city",
        "state",
    ]

    ordering = [
        "state",
        "city",
    ]

    readonly_fields = [
        "created_at",
        "updated_at",
    ]


@admin.register(ShippingAddress)
class ShippingAddressAdmin(admin.ModelAdmin):
    list_display = [
        "recipient_name",
        "user",
        "delivery_location",
        "phone_number",
        "label",
        "is_default",
    ]

    list_filter = [
        "label",
        "is_default",
        "delivery_location__state",
    ]

    search_fields = [
        "recipient_name",
        "phone_number",
        "user__email",
        "delivery_location__city",
        "delivery_location__state",
    ]

    autocomplete_fields = [
        "user",
        "delivery_location",
    ]

    readonly_fields = [
        "country",
        "created_at",
        "updated_at",
    ]
