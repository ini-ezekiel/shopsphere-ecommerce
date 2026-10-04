from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import EmailVerificationToken, User


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display_links = ["id", "email"]
    list_display = [
        "id",
        "email",
        "username",
        "is_email_verified",
        "is_staff",
        "is_active",
    ]

    list_filter = [
        "is_email_verified",
        "is_staff",
        "is_active",
    ]

    search_fields = [
        "email",
        "username",
        "first_name",
        "last_name",
    ]

    ordering = ["id"]

    fieldsets = UserAdmin.fieldsets + (
        (
            "Email verification",
            {
                "fields": (
                    "is_email_verified",
                    "email_verified_at",
                )
            },
        ),
    )

    add_fieldsets = UserAdmin.add_fieldsets + (
        (
            "Account details",
            {
                "fields": (
                    "email",
                    "is_email_verified",
                )
            },
        ),
    )


@admin.register(EmailVerificationToken)
class EmailVerificationTokenAdmin(admin.ModelAdmin):
    list_display = [
        "user",
        "created_at",
        "expires_at",
    ]

    search_fields = [
        "user__email",
        "user__username",
    ]

    readonly_fields = [
        "token_hash",
        "created_at",
        "expires_at",
    ]