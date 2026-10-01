from django.contrib import admin

from .models import Shipment


@admin.register(Shipment)
class ShipmentAdmin(admin.ModelAdmin):
    list_display = [
        "order",
        "status",
        "carrier",
        "tracking_number",
        "shipped_at",
        "delivered_at",
        "updated_at",
    ]

    list_filter = [
        "status",
        "carrier",
        "shipped_at",
        "delivered_at",
        "created_at",
    ]

    search_fields = [
        "order__order_number",
        "order__user__email",
        "carrier",
        "tracking_number",
    ]

    list_select_related = [
        "order",
        "order__user",
        "created_by",
    ]

    readonly_fields = [
        "order",
        "status",
        "carrier",
        "tracking_number",
        "shipped_at",
        "delivered_at",
        "created_by",
        "created_at",
        "updated_at",
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
