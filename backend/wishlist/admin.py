from django.contrib import admin

from .models import WishlistItem


@admin.register(WishlistItem)
class WishlistItemAdmin(admin.ModelAdmin):
    list_display = [
        "user",
        "product",
        "created_at",
    ]

    search_fields = [
        "user__email",
        "user__username",
        "product__name",
        "product__slug",
    ]

    list_select_related = [
        "user",
        "product",
    ]

    ordering = [
        "-created_at",
    ]

    date_hierarchy = "created_at"

    readonly_fields = [
        "user",
        "product",
        "created_at",
    ]

    def has_add_permission(self, request):
        return False
