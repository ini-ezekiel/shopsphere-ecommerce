from django.contrib import admin

from .models import Notification


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = [
        "title",
        "user",
        "event_type",
        "read_status",
        "created_at",
    ]

    list_filter = [
        "event_type",
        "read_at",
        "created_at",
    ]

    search_fields = [
        "title",
        "message",
        "user__email",
        "deduplication_key",
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
        "event_type",
        "title",
        "message",
        "link",
        "metadata",
        "deduplication_key",
        "read_at",
        "created_at",
    ]

    fieldsets = [
        (
            "Notification",
            {
                "fields": [
                    "user",
                    "event_type",
                    "title",
                    "message",
                    "link",
                ]
            },
        ),
        (
            "Delivery data",
            {
                "fields": [
                    "metadata",
                    "deduplication_key",
                    "read_at",
                    "created_at",
                ]
            },
        ),
    ]

    @admin.display(
        boolean=True,
        description="Read",
    )
    def read_status(self, obj):
        return obj.is_read

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
