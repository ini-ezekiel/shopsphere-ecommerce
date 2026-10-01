from django.contrib import admin

from .models import (
    Payment,
    Refund,
    WebhookEvent,
)


class RefundInline(admin.StackedInline):
    model = Refund
    extra = 0
    max_num = 1
    can_delete = False
    show_change_link = True

    fields = [
        "reference",
        "status",
        "provider_status",
        "amount",
        "currency",
        "reason",
        "requested_by_email",
        "processed_at",
        "created_at",
        "updated_at",
    ]

    readonly_fields = fields

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = [
        "reference",
        "order",
        "provider",
        "status",
        "amount",
        "currency",
        "channel",
        "created_at",
    ]

    list_filter = [
        "provider",
        "status",
        "currency",
        "channel",
        "created_at",
    ]

    search_fields = [
        "reference",
        "order__order_number",
        "order__user__email",
        "provider_transaction_id",
    ]

    list_select_related = [
        "order",
        "order__user",
    ]

    date_hierarchy = "created_at"

    ordering = [
        "-created_at",
    ]

    readonly_fields = [
        "order",
        "provider",
        "reference",
        "idempotency_key",
        "status",
        "provider_status",
        "amount",
        "amount_subunit",
        "currency",
        "authorization_url",
        "access_code",
        "provider_transaction_id",
        "channel",
        "gateway_response",
        "failure_message",
        "initialization_response",
        "verification_response",
        "paid_at",
        "verified_at",
        "created_at",
        "updated_at",
    ]

    fieldsets = [
        (
            "Payment",
            {
                "fields": [
                    "reference",
                    "order",
                    "provider",
                    "status",
                    "provider_status",
                    "idempotency_key",
                ]
            },
        ),
        (
            "Amount",
            {
                "fields": [
                    "amount",
                    "amount_subunit",
                    "currency",
                ]
            },
        ),
        (
            "Paystack checkout",
            {
                "fields": [
                    "authorization_url",
                    "access_code",
                    "provider_transaction_id",
                    "channel",
                    "gateway_response",
                ]
            },
        ),
        (
            "Provider responses",
            {
                "fields": [
                    "failure_message",
                    "initialization_response",
                    "verification_response",
                ],
                "classes": [
                    "collapse",
                ],
            },
        ),
        (
            "Timestamps",
            {
                "fields": [
                    "paid_at",
                    "verified_at",
                    "created_at",
                    "updated_at",
                ]
            },
        ),
    ]

    inlines = [
        RefundInline,
    ]

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Refund)
class RefundAdmin(admin.ModelAdmin):
    list_display = [
        "reference",
        "payment",
        "status",
        "provider_status",
        "amount",
        "currency",
        "requested_by_email",
        "created_at",
        "processed_at",
    ]

    list_filter = [
        "provider",
        "status",
        "provider_status",
        "currency",
        "created_at",
        "processed_at",
    ]

    search_fields = [
        "reference",
        "provider_refund_id",
        "payment__reference",
        "payment__order__order_number",
        "payment__order__user__email",
        "requested_by_email",
        "reason",
    ]

    list_select_related = [
        "payment",
        "payment__order",
        "payment__order__user",
        "requested_by",
    ]

    date_hierarchy = "created_at"

    ordering = [
        "-created_at",
    ]

    readonly_fields = [
        "payment",
        "requested_by",
        "requested_by_email",
        "reference",
        "provider",
        "provider_refund_id",
        "status",
        "provider_status",
        "amount",
        "amount_subunit",
        "currency",
        "reason",
        "failure_message",
        "initialization_response",
        "latest_webhook_payload",
        "processed_at",
        "created_at",
        "updated_at",
    ]

    fieldsets = [
        (
            "Refund",
            {
                "fields": [
                    "reference",
                    "payment",
                    "provider",
                    "provider_refund_id",
                    "status",
                    "provider_status",
                ]
            },
        ),
        (
            "Request",
            {
                "fields": [
                    "requested_by",
                    "requested_by_email",
                    "reason",
                ]
            },
        ),
        (
            "Amount",
            {
                "fields": [
                    "amount",
                    "amount_subunit",
                    "currency",
                ]
            },
        ),
        (
            "Provider responses",
            {
                "fields": [
                    "failure_message",
                    "initialization_response",
                    "latest_webhook_payload",
                ],
                "classes": [
                    "collapse",
                ],
            },
        ),
        (
            "Timestamps",
            {
                "fields": [
                    "processed_at",
                    "created_at",
                    "updated_at",
                ]
            },
        ),
    ]

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(WebhookEvent)
class WebhookEventAdmin(admin.ModelAdmin):
    list_display = [
        "event_type",
        "reference",
        "provider",
        "processed",
        "created_at",
    ]

    list_filter = [
        "provider",
        "event_type",
        "processed",
        "created_at",
    ]

    search_fields = [
        "reference",
        "payload_hash",
        "event_type",
    ]

    date_hierarchy = "created_at"

    ordering = [
        "-created_at",
    ]

    readonly_fields = [
        "provider",
        "event_type",
        "reference",
        "payload_hash",
        "payload",
        "processed",
        "processed_at",
        "processing_error",
        "created_at",
    ]

    fieldsets = [
        (
            "Webhook event",
            {
                "fields": [
                    "provider",
                    "event_type",
                    "reference",
                    "payload_hash",
                    "processed",
                    "processed_at",
                    "processing_error",
                    "created_at",
                ]
            },
        ),
        (
            "Payload",
            {
                "fields": [
                    "payload",
                ],
                "classes": [
                    "collapse",
                ],
            },
        ),
    ]

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False