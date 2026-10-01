from django.contrib import admin

from .models import Review


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = [
        "product",
        "user",
        "rating",
        "is_visible",
        "created_at",
        "updated_at",
    ]

    list_filter = [
        "rating",
        "is_visible",
        "created_at",
        "updated_at",
    ]

    search_fields = [
        "product__name",
        "user__email",
        "user__username",
        "order_item__order__order_number",
        "title",
        "comment",
    ]

    list_select_related = [
        "product",
        "user",
        "order_item",
        "order_item__order",
    ]

    ordering = [
        "-created_at",
    ]

    readonly_fields = [
        "user",
        "product",
        "order_item",
        "rating",
        "title",
        "comment",
        "created_at",
        "updated_at",
    ]

    fields = [
        "user",
        "product",
        "order_item",
        "rating",
        "title",
        "comment",
        "is_visible",
        "created_at",
        "updated_at",
    ]

    actions = [
        "hide_selected_reviews",
        "show_selected_reviews",
    ]

    @admin.action(
        description="Hide selected reviews",
    )
    def hide_selected_reviews(
        self,
        request,
        queryset,
    ):
        updated_count = queryset.update(
            is_visible=False,
        )

        self.message_user(
            request,
            f"{updated_count} review(s) hidden.",
        )

    @admin.action(
        description="Show selected reviews",
    )
    def show_selected_reviews(
        self,
        request,
        queryset,
    ):
        updated_count = queryset.update(
            is_visible=True,
        )

        self.message_user(
            request,
            f"{updated_count} review(s) made visible.",
        )

    def has_add_permission(self, request):
        return False

    def has_delete_permission(
        self,
        request,
        obj=None,
    ):
        return False
