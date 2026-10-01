import hashlib
import secrets

import string

from django.utils.text import slugify

from django.conf import settings
from django.core.mail import send_mail
from django.utils import timezone

from .models import EmailVerificationToken


from django.contrib.auth.tokens import default_token_generator
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode

from google.auth.transport import requests as google_requests
from google.oauth2 import id_token

import hashlib
import secrets

from django.contrib.auth.hashers import make_password


def hash_verification_token(raw_token):
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


def send_verification_email(user):
    if user.is_email_verified:
        return False

    raw_token = secrets.token_urlsafe(32)
    token_hash = hash_verification_token(raw_token)

    EmailVerificationToken.objects.update_or_create(
        user=user,
        defaults={
            "token_hash": token_hash,
            "expires_at": (timezone.now() + settings.EMAIL_VERIFICATION_TOKEN_LIFETIME),
        },
    )

    verification_url = f"{settings.FRONTEND_URL}/verify-email" f"#token={raw_token}"

    message = (
        f"Hello {user.username},\n\n"
        "Thank you for creating an account.\n\n"
        "Verify your email address using this link:\n"
        f"{verification_url}\n\n"
        "This link expires in 24 hours. "
        "If you did not create this account, "
        "you can ignore this email."
    )

    send_mail(
        subject="Verify your email address",
        message=message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user.email],
        fail_silently=False,
    )

    return True


def send_password_reset_email(user):
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    token = default_token_generator.make_token(user)

    reset_url = f"{settings.FRONTEND_URL}/reset-password?uid={uid}&token={token}"

    message = (
        f"Hello {user.username},\n\n"
        "A password reset was requested for your account.\n\n"
        "Your password-reset details are:\n\n"
        f"UID: {uid}\n"
        f"Token: {token}\n\n"
        "You can also use this reset link:\n"
        f"{reset_url}\n\n"
        "If you did not request this reset, "
        "you can ignore this email."
    )

    send_mail(
        subject="Reset your password",
        message=message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user.email],
        fail_silently=False,
    )


# GOOGLE CREDENTIALS VERIFICATION


def verify_google_credential(credential):
    client_id = settings.GOOGLE_OAUTH_CLIENT_ID
    if not client_id:
        raise ValueError("Google authentication is not configured.")
    payload = id_token.verify_oauth2_token(
        credential,
        google_requests.Request(),
        client_id,
    )
    subject = payload.get("sub")
    email = payload.get("email")
    email_verified = payload.get("email_verified")

    if not subject or not email or email_verified is not True:
        raise ValueError("The Google account could not be verified.")
    return payload


def generate_unique_username(first_name, email, User):
    source = first_name or email.split("@")[0]
    base = slugify(source).replace("-", "_") or "user"
    base = base[:140]
    while True:
        suffix = "".join(secrets.choice(string.ascii_lowercase) for _ in range(6))
        username = f"{base}_{suffix}"
        if not User.objects.filter(username=username).exists():
            return username


def generate_registration_otp():
    return f"{secrets.randbelow(1_000_000):06d}"


def hash_registration_otp(otp):
    return make_password(otp)


def generate_registration_completion_token():
    return secrets.token_urlsafe(32)


def hash_registration_completion_token(token):
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def send_registration_otp(email, otp):
    expiry_minutes = settings.REGISTRATION_OTP_EXPIRY_MINUTES

    send_mail(
        subject="Your registration verification code",
        message=(
            "Use the verification code below to continue "
            "creating your account:\n\n"
            f"{otp}\n\n"
            f"This code expires in {expiry_minutes} minutes.\n"
            "If you did not request this code, you can ignore "
            "this email."
        ),
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[email],
        fail_silently=False,
    )
