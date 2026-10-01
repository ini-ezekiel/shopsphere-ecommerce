from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.db import models

import uuid
from django.db.models.functions import Lower


class User(AbstractUser):
    email = models.EmailField(unique=True)

    is_email_verified = models.BooleanField(
        default=False,
    )

    email_verified_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    username_changed_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                Lower("username"),
                name="unique_user_username_case_insensitive",
            ),
        ]

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["username"]

# USERNAME TRACKING LOGIC
class UsernameHistory(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="username_history",
    )
    old_username = models.CharField(max_length=150)
    new_username = models.CharField(max_length=150)
    changed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-changed_at"]
        verbose_name_plural = "username history"
        indexes = [
            models.Index(fields=["old_username"]),
            models.Index(fields=["user", "changed_at"]),
        ]

    def __str__(self):
        return (
            f"{self.old_username} → "
            f"{self.new_username}"
        )

# EMAIL VERIFIACTION TOKEN


class EmailVerificationToken(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="email_verification_token",
    )

    token_hash = models.CharField(
        max_length=64,
        unique=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    expires_at = models.DateTimeField(
        db_index=True,
    )

    def __str__(self):
        return f"Email verification token for {self.user.email}"


# GOOGLE AUTH


class SocialIdentity(models.Model):
    class Provider(models.TextChoices):
        GOOGLE = "google", "Google"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="social_identities",
    )
    provider = models.CharField(
        max_length=30,
        choices=Provider.choices,
    )
    subject = models.CharField(max_length=255)
    email_at_link = models.EmailField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["provider", "subject"],
                name="unique_social_provider_subject",
            ),
            models.UniqueConstraint(
                fields=["user", "provider"],
                name="unique_social_provider_per_user",
            ),
        ]

    def __str__(self):
        return f"{self.user.email} — {self.provider}"


# REGISTRATION PENDING CONTROL


class PendingRegistration(models.Model):
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    email = models.EmailField(unique=True)

    otp_hash = models.CharField(max_length=128)
    otp_expires_at = models.DateTimeField()
    otp_attempts = models.PositiveSmallIntegerField(default=0)
    last_sent_at = models.DateTimeField()

    verified_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    completion_token_hash = models.CharField(
        max_length=64,
        blank=True,
    )
    completion_token_expires_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    completed_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["otp_expires_at"]),
            models.Index(fields=["completion_token_expires_at"]),
        ]

    def __str__(self):
        return f"Pending registration for {self.email}"
