from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError as DjangoValidationError
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers, status
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from django.db import transaction, IntegrityError
from django.utils import timezone
import hmac


from rest_framework.exceptions import AuthenticationFailed

from .models import EmailVerificationToken, UsernameHistory
from .services import (
    hash_verification_token,
    generate_unique_username,
    verify_google_credential,
    generate_registration_otp,
    hash_registration_otp,
    send_registration_otp,
    generate_registration_completion_token,
    hash_registration_completion_token,
)

from datetime import timedelta
from django.conf import settings
from .models import PendingRegistration


from django.contrib.auth.password_validation import (
    validate_password,
)
from django.contrib.auth.tokens import (
    default_token_generator,
)

from django.utils.encoding import force_str
from django.utils.http import urlsafe_base64_decode
from rest_framework_simplejwt.token_blacklist.models import (
    BlacklistedToken,
    OutstandingToken,
)

from rest_framework_simplejwt.tokens import RefreshToken

from .models import SocialIdentity


from google.auth.exceptions import TransportError
from rest_framework.exceptions import APIException


from django.contrib.auth.hashers import (
    check_password,
    make_password,
)

User = get_user_model()


# REGISTRATION EXPIRES AFTER 24HRS NEW OTP NEEDED


class RegistrationStartSerializer(serializers.Serializer):
    email = serializers.EmailField(
        write_only=True,
        max_length=254,
    )

    def validate_email(self, value):
        return value.strip().lower()

    def create(self, validated_data):
        email = validated_data["email"]
        now = timezone.now()

        cooldown = timedelta(
            seconds=(settings.REGISTRATION_OTP_RESEND_COOLDOWN_SECONDS)
        )
        otp_expiry = timedelta(minutes=settings.REGISTRATION_OTP_EXPIRY_MINUTES)

        with transaction.atomic():
            pending = (
                PendingRegistration.objects.select_for_update()
                .filter(email=email)
                .first()
            )

            if (
                pending
                and pending.last_sent_at
                and now < pending.last_sent_at + cooldown
            ):
                return {
                    "registration_id": str(pending.id),
                }

            otp = generate_registration_otp()
            otp_hash = hash_registration_otp(otp)

            if pending:
                pending.otp_hash = otp_hash
                pending.otp_expires_at = now + otp_expiry
                pending.otp_attempts = 0
                pending.last_sent_at = now
                pending.verified_at = None
                pending.completion_token_hash = ""
                pending.completion_token_expires_at = None
                pending.completed_at = None
                pending.save(
                    update_fields=[
                        "otp_hash",
                        "otp_expires_at",
                        "otp_attempts",
                        "last_sent_at",
                        "verified_at",
                        "completion_token_hash",
                        "completion_token_expires_at",
                        "completed_at",
                        "updated_at",
                    ]
                )
            else:
                pending = PendingRegistration.objects.create(
                    email=email,
                    otp_hash=otp_hash,
                    otp_expires_at=now + otp_expiry,
                    otp_attempts=0,
                    last_sent_at=now,
                )

            email_already_registered = User.objects.filter(email__iexact=email).exists()

            if not email_already_registered:
                transaction.on_commit(
                    lambda: send_registration_otp(
                        email,
                        otp,
                    )
                )

        return {
            "registration_id": str(pending.id),
        }


# REGISTRATION VERIFICATION


class RegistrationVerifySerializer(serializers.Serializer):
    registration_id = serializers.UUIDField(write_only=True)
    otp = serializers.RegexField(
        regex=r"^\d{6}$",
        write_only=True,
        error_messages={
            "invalid": "Enter a valid six-digit code.",
        },
    )

    def create(self, validated_data):
        registration_id = validated_data["registration_id"]
        submitted_otp = validated_data["otp"]
        now = timezone.now()

        completion_token = None
        error_message = None

        with transaction.atomic():
            pending = (
                PendingRegistration.objects.select_for_update()
                .filter(id=registration_id)
                .first()
            )

            if not pending:
                error_message = "Invalid or expired verification code."

            elif pending.completed_at is not None:
                error_message = "Invalid or expired verification code."

            elif User.objects.filter(email__iexact=pending.email).exists():
                error_message = "Invalid or expired verification code."

            elif pending.otp_expires_at <= now:
                error_message = "Invalid or expired verification code."

            elif pending.otp_attempts >= settings.REGISTRATION_OTP_MAX_ATTEMPTS:
                error_message = "Invalid or expired verification code."

            elif not check_password(
                submitted_otp,
                pending.otp_hash,
            ):
                pending.otp_attempts += 1
                pending.save(
                    update_fields=[
                        "otp_attempts",
                        "updated_at",
                    ]
                )

                error_message = "Invalid or expired verification code."

            else:
                completion_token = generate_registration_completion_token()

                completion_expiry = timedelta(
                    minutes=(settings.REGISTRATION_COMPLETION_TOKEN_EXPIRY_MINUTES)
                )

                pending.otp_hash = make_password(None)
                pending.verified_at = now
                pending.completion_token_hash = hash_registration_completion_token(
                    completion_token
                )
                pending.completion_token_expires_at = now + completion_expiry

                pending.save(
                    update_fields=[
                        "otp_hash",
                        "verified_at",
                        "completion_token_hash",
                        "completion_token_expires_at",
                        "updated_at",
                    ]
                )

        if error_message:
            raise serializers.ValidationError(
                {
                    "otp": error_message,
                }
            )

        return {
            "registration_token": completion_token,
            "expires_in_minutes": (
                settings.REGISTRATION_COMPLETION_TOKEN_EXPIRY_MINUTES
            ),
        }


# REGISTRATION COMPLETE SERIALIZERS


class RegistrationCompleteSerializer(serializers.Serializer):
    registration_id = serializers.UUIDField(write_only=True)
    registration_token = serializers.CharField(
        write_only=True,
        trim_whitespace=False,
    )
    first_name = serializers.CharField(max_length=150)
    last_name = serializers.CharField(max_length=150)
    username = serializers.RegexField(
        regex=r"^[a-z0-9_]{3,30}$",
        max_length=30,
        error_messages={
            "invalid": (
                "Username must contain 3 to 30 lowercase "
                "letters, numbers or underscores."
            ),
        },
    )
    password = serializers.CharField(
        write_only=True,
        trim_whitespace=False,
    )
    password2 = serializers.CharField(
        write_only=True,
        trim_whitespace=False,
    )

    def validate_first_name(self, value):
        value = value.strip()

        if not value:
            raise serializers.ValidationError("First name is required.")

        return value

    def validate_last_name(self, value):
        value = value.strip()

        if not value:
            raise serializers.ValidationError("Last name is required.")

        return value

    def validate_username(self, value):
        return value.strip().lower()

    def validate(self, attrs):
        if attrs["password"] != attrs["password2"]:
            raise serializers.ValidationError(
                {
                    "password2": "Passwords do not match.",
                }
            )

        return attrs

    def create(self, validated_data):
        registration_id = validated_data["registration_id"]
        registration_token = validated_data["registration_token"]
        username = validated_data["username"]
        first_name = validated_data["first_name"]
        last_name = validated_data["last_name"]
        password = validated_data["password"]
        now = timezone.now()

        submitted_token_hash = hash_registration_completion_token(registration_token)

        try:
            with transaction.atomic():
                pending = (
                    PendingRegistration.objects.select_for_update()
                    .filter(id=registration_id)
                    .first()
                )

                token_is_valid = (
                    pending is not None
                    and pending.verified_at is not None
                    and pending.completed_at is None
                    and bool(pending.completion_token_hash)
                    and (pending.completion_token_expires_at is not None)
                    and (pending.completion_token_expires_at > now)
                    and hmac.compare_digest(
                        pending.completion_token_hash,
                        submitted_token_hash,
                    )
                )

                if not token_is_valid:
                    raise serializers.ValidationError(
                        {
                            "registration_token": (
                                "Invalid or expired " "registration token."
                            )
                        }
                    )

                if User.objects.filter(email__iexact=pending.email).exists():
                    raise serializers.ValidationError(
                        {
                            "registration_token": (
                                "Invalid or expired " "registration token."
                            )
                        }
                    )

                username_unavailable = (
                    User.objects.filter(username__iexact=username).exists()
                    or UsernameHistory.objects.filter(
                        old_username__iexact=username
                    ).exists()
                )

                if username_unavailable:
                    raise serializers.ValidationError(
                        {"username": ("This username is unavailable.")}
                    )

                candidate_user = User(
                    username=username,
                    email=pending.email,
                    first_name=first_name,
                    last_name=last_name,
                )

                try:
                    validate_password(
                        password,
                        user=candidate_user,
                    )
                except DjangoValidationError as exc:
                    raise serializers.ValidationError(
                        {
                            "password": list(exc.messages),
                        }
                    ) from exc

                user = User.objects.create_user(
                    username=username,
                    email=pending.email,
                    password=password,
                    first_name=first_name,
                    last_name=last_name,
                    is_email_verified=True,
                    email_verified_at=now,
                )

                pending.completed_at = now
                pending.completion_token_hash = ""
                pending.completion_token_expires_at = None
                pending.save(
                    update_fields=[
                        "completed_at",
                        "completion_token_hash",
                        "completion_token_expires_at",
                        "updated_at",
                    ]
                )

                refresh = RefreshToken.for_user(user)

        except IntegrityError as exc:
            raise serializers.ValidationError(
                {
                    "detail": (
                        "Registration could not be completed. "
                        "Please restart the registration process."
                    )
                }
            ) from exc

        return {
            "refresh": str(refresh),
            "access": str(refresh.access_token),
            "user": {
                "id": user.id,
                "email": user.email,
                "username": user.username,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "is_email_verified": (user.is_email_verified),
            },
        }


class LoginSerializer(TokenObtainPairSerializer):
    default_error_messages = {"no_active_account": "Invalid email or password."}

    def validate(self, attrs):
        data = super().validate(attrs)

        if not self.user.is_email_verified:
            raise AuthenticationFailed(
                "Email verification is required.",
                code="email_not_verified",
            )

        return data


class AccountProfileSerializer(serializers.ModelSerializer):
    has_password = serializers.SerializerMethodField()
    google_linked = serializers.SerializerMethodField()

    class Meta:
        model = User

        fields = [
            "id",
            "username",
            "email",
            "first_name",
            "last_name",
            "date_joined",
            "has_password",
            "google_linked",
            "is_staff",
        ]

        read_only_fields = [
            "id",
            "username",
            "email",
            "date_joined",
            "has_password",
            "google_linked",
            "is_staff",
        ]

    def get_has_password(self, obj):
        return obj.has_usable_password()

    def get_google_linked(self, obj):
        return obj.social_identities.filter(
            provider=SocialIdentity.Provider.GOOGLE,
        ).exists()


class PasswordChangeSerializer(serializers.Serializer):
    old_password = serializers.CharField(
        write_only=True,
        required=True,
    )

    new_password = serializers.CharField(
        write_only=True,
        required=True,
    )

    new_password2 = serializers.CharField(
        write_only=True,
        required=True,
    )

    def validate(self, attrs):
        user = self.context["request"].user

        if not user.check_password(attrs["old_password"]):
            raise serializers.ValidationError(
                {"old_password": "Current password is incorrect."}
            )

        if attrs["new_password"] != attrs["new_password2"]:
            raise serializers.ValidationError(
                {"new_password2": "New passwords do not match."}
            )

        if user.check_password(attrs["new_password"]):
            raise serializers.ValidationError(
                {
                    "new_password": (
                        "The new password must be different "
                        "from the current password."
                    )
                }
            )

        try:
            validate_password(
                attrs["new_password"],
                user=user,
            )
        except DjangoValidationError as error:
            raise serializers.ValidationError({"new_password": list(error.messages)})

        return attrs

    def save(self, **kwargs):
        user = self.context["request"].user
        user.set_password(self.validated_data["new_password"])
        user.save(update_fields=["password"])

        return user


class EmailVerificationSerializer(serializers.Serializer):
    token = serializers.CharField(
        write_only=True,
        trim_whitespace=True,
    )

    def create(self, validated_data):
        token_hash = hash_verification_token(validated_data["token"])

        with transaction.atomic():
            try:
                token_record = (
                    EmailVerificationToken.objects.select_for_update()
                    .select_related("user")
                    .get(token_hash=token_hash)
                )
            except EmailVerificationToken.DoesNotExist:
                raise serializers.ValidationError(
                    {"token": ("Invalid or expired " "verification token.")}
                )

            if token_record.expires_at <= timezone.now():
                token_record.delete()

                raise serializers.ValidationError(
                    {"token": ("Invalid or expired " "verification token.")}
                )

            user = token_record.user

            user.is_email_verified = True
            user.email_verified_at = timezone.now()

            user.save(
                update_fields=[
                    "is_email_verified",
                    "email_verified_at",
                ]
            )

            token_record.delete()

        return user


class EmailVerificationResendSerializer(serializers.Serializer):
    email = serializers.EmailField()

    def validate_email(self, value):
        return value.strip().lower()


class PasswordResetRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()

    def validate_email(self, value):
        return value.strip().lower()


class PasswordResetConfirmSerializer(serializers.Serializer):
    uid = serializers.CharField(write_only=True)
    token = serializers.CharField(write_only=True)

    new_password = serializers.CharField(
        write_only=True,
    )

    new_password2 = serializers.CharField(
        write_only=True,
    )

    default_error_messages = {
        "invalid_token": ("The password reset link is invalid or expired."),
    }

    def validate(self, attrs):
        try:
            user_id = force_str(urlsafe_base64_decode(attrs["uid"]))

            user = User.objects.get(
                pk=user_id,
                is_active=True,
            )
        except (
            TypeError,
            ValueError,
            OverflowError,
            User.DoesNotExist,
        ):
            self.fail("invalid_token")

        if not default_token_generator.check_token(
            user,
            attrs["token"],
        ):
            self.fail("invalid_token")

        if attrs["new_password"] != attrs["new_password2"]:
            raise serializers.ValidationError(
                {"new_password2": ("Passwords do not match.")}
            )

        if user.check_password(attrs["new_password"]):
            raise serializers.ValidationError(
                {
                    "new_password": (
                        "The new password must be different "
                        "from the current password."
                    )
                }
            )

        try:
            validate_password(
                attrs["new_password"],
                user=user,
            )
        except DjangoValidationError as error:
            raise serializers.ValidationError(
                {
                    "new_password": error.messages,
                }
            ) from error

        attrs["user"] = user
        return attrs

    def save(self):
        user = self.validated_data["user"]
        token = self.validated_data["token"]
        new_password = self.validated_data["new_password"]

        with transaction.atomic():
            locked_user = User.objects.select_for_update().get(pk=user.pk)

            if not default_token_generator.check_token(
                locked_user,
                token,
            ):
                self.fail("invalid_token")

            if locked_user.check_password(new_password):
                raise serializers.ValidationError(
                    {
                        "new_password": (
                            "The new password must be different "
                            "from the current password."
                        )
                    }
                )

            locked_user.set_password(new_password)
            locked_user.save(update_fields=["password"])

            outstanding_tokens = OutstandingToken.objects.filter(
                user=locked_user,
            )

            for outstanding_token in outstanding_tokens:
                BlacklistedToken.objects.get_or_create(
                    token=outstanding_token,
                )

        return locked_user


class GoogleAuthenticationUnavailable(APIException):
    status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    default_detail = "Google authentication is temporarily unavailable."
    default_code = "google_authentication_unavailable"


class GoogleAuthenticationSerializer(serializers.Serializer):
    credential = serializers.CharField(
        write_only=True,
        trim_whitespace=False,
    )

    def validate(self, attrs):
        try:
            payload = verify_google_credential(attrs["credential"])
        except TransportError as exc:
            raise GoogleAuthenticationUnavailable() from exc
        except ValueError:
            raise serializers.ValidationError(
                {"credential": ("The Google credential is invalid or expired.")}
            )

        subject = payload["sub"]
        email = payload["email"].strip().lower()
        first_name = payload.get("given_name", "").strip()[:150]
        last_name = payload.get("family_name", "").strip()[:150]

        identity = (
            SocialIdentity.objects.select_related("user")
            .filter(
                provider=SocialIdentity.Provider.GOOGLE,
                subject=subject,
            )
            .first()
        )

        is_new_user = False

        if identity:
            user = identity.user
        else:
            existing_user = User.objects.filter(email__iexact=email).first()

            if existing_user:
                raise serializers.ValidationError(
                    {
                        "credential": (
                            "Google sign-in could not be completed."
                            "Try another sign-in method or contact support."
                        )
                    }
                )

            try:
                with transaction.atomic():
                    username = generate_unique_username(
                        first_name,
                        email,
                        User,
                    )

                    user = User(
                        username=username,
                        email=email,
                        first_name=first_name,
                        last_name=last_name,
                        is_email_verified=True,
                        email_verified_at=timezone.now(),
                    )
                    user.set_unusable_password()
                    user.save()

                    SocialIdentity.objects.create(
                        user=user,
                        provider=SocialIdentity.Provider.GOOGLE,
                        subject=subject,
                        email_at_link=email,
                    )

                    is_new_user = True

            except IntegrityError:
                identity = (
                    SocialIdentity.objects.select_related("user")
                    .filter(
                        provider=(SocialIdentity.Provider.GOOGLE),
                        subject=subject,
                    )
                    .first()
                )

                if not identity:
                    raise serializers.ValidationError(
                        {
                            "credential": (
                                "Google authentication could not be "
                                "completed. Please try again."
                            )
                        }
                    )

                user = identity.user
                is_new_user = False

        if not user.is_active:
            raise serializers.ValidationError(
                {"credential": ("This account is currently unavailable.")}
            )

        refresh = RefreshToken.for_user(user)

        return {
            "refresh": str(refresh),
            "access": str(refresh.access_token),
            "is_new_user": is_new_user,
            "user": {
                "id": user.id,
                "email": user.email,
                "username": user.username,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "is_email_verified": user.is_email_verified,
            },
        }


# SECURE GOOGLE-LINK


class GoogleAccountLinkSerializer(serializers.Serializer):
    credential = serializers.CharField(
        write_only=True,
        trim_whitespace=False,
    )

    def validate(self, attrs):
        user = self.context["request"].user

        try:
            payload = verify_google_credential(attrs["credential"])
        except TransportError as exc:
            raise GoogleAuthenticationUnavailable() from exc
        except ValueError:
            raise serializers.ValidationError(
                {"credential": ("The Google credential is invalid " "or expired.")}
            )

        subject = payload["sub"]
        google_email = payload["email"].strip().lower()

        if google_email != user.email.strip().lower():
            raise serializers.ValidationError(
                {
                    "credential": (
                        "The Google account email must match " "your account email."
                    )
                }
            )

        try:
            with transaction.atomic():
                locked_user = User.objects.select_for_update().get(pk=user.pk)

                subject_identity = (
                    SocialIdentity.objects.select_for_update()
                    .filter(
                        provider=(SocialIdentity.Provider.GOOGLE),
                        subject=subject,
                    )
                    .first()
                )

                if subject_identity and subject_identity.user_id != locked_user.id:
                    raise serializers.ValidationError(
                        {
                            "credential": (
                                "This Google account is already "
                                "linked to another account."
                            )
                        }
                    )

                user_identity = (
                    SocialIdentity.objects.select_for_update()
                    .filter(
                        user=locked_user,
                        provider=(SocialIdentity.Provider.GOOGLE),
                    )
                    .first()
                )

                if user_identity:
                    if user_identity.subject == subject:
                        attrs["already_linked"] = True
                        return attrs

                    raise serializers.ValidationError(
                        {
                            "credential": (
                                "A different Google account is "
                                "already linked to this account."
                            )
                        }
                    )

                SocialIdentity.objects.create(
                    user=locked_user,
                    provider=SocialIdentity.Provider.GOOGLE,
                    subject=subject,
                    email_at_link=google_email,
                )

        except IntegrityError:
            identity = SocialIdentity.objects.filter(
                user=user,
                provider=SocialIdentity.Provider.GOOGLE,
                subject=subject,
            ).first()

            if not identity:
                raise serializers.ValidationError(
                    {
                        "credential": (
                            "Google account linking could not "
                            "be completed. Please try again."
                        )
                    }
                )

            attrs["already_linked"] = True
            return attrs

        attrs["already_linked"] = False
        return attrs


# GOOGLE UNLINK

# PREVENT
# Google-only users from locking themselves out.
# Unlinking without the current password.
# Unlinking another user’s Google identity.


class GoogleAccountUnlinkSerializer(serializers.Serializer):
    current_password = serializers.CharField(
        write_only=True,
        trim_whitespace=False,
    )

    def create(self, validated_data):
        request_user = self.context["request"].user

        with transaction.atomic():
            user = User.objects.select_for_update().get(pk=request_user.pk)

            if not user.has_usable_password():
                raise serializers.ValidationError(
                    {
                        "non_field_errors": (
                            "Google cannot be unlinked because "
                            "it is your only sign-in method."
                        )
                    }
                )

            if not user.check_password(validated_data["current_password"]):
                raise serializers.ValidationError(
                    {"current_password": ("The password is incorrect.")}
                )

            identity = (
                SocialIdentity.objects.select_for_update()
                .filter(
                    user=user,
                    provider=SocialIdentity.Provider.GOOGLE,
                )
                .first()
            )

            if not identity:
                raise serializers.ValidationError(
                    {"non_field_errors": ("No Google account is linked.")}
                )

            identity.delete()

        return {"unlinked": True}


# GIVING CONTROL TO USERS SIGNING UP WITH GOOGLE AUTH TO CHANGE SET PASSWORDS
class GoogleSetPasswordSerializer(serializers.Serializer):
    credential = serializers.CharField(
        write_only=True,
        trim_whitespace=False,
    )
    password = serializers.CharField(
        write_only=True,
        trim_whitespace=False,
    )
    password2 = serializers.CharField(
        write_only=True,
        trim_whitespace=False,
    )

    def validate(self, attrs):
        user = self.context["request"].user

        if user.has_usable_password():
            raise serializers.ValidationError(
                {
                    "non_field_errors": (
                        "This account already has a password. "
                        "Use the password-change endpoint instead."
                    )
                }
            )

        if attrs["password"] != attrs["password2"]:
            raise serializers.ValidationError(
                {"password2": ("The passwords do not match.")}
            )

        try:
            payload = verify_google_credential(attrs["credential"])
        except TransportError as exc:
            raise GoogleAuthenticationUnavailable() from exc
        except ValueError:
            raise serializers.ValidationError(
                {"credential": ("The Google credential is invalid " "or expired.")}
            )

        subject = payload["sub"]
        google_email = payload["email"].strip().lower()

        identity_exists = SocialIdentity.objects.filter(
            user=user,
            provider=SocialIdentity.Provider.GOOGLE,
            subject=subject,
        ).exists()

        if not identity_exists or google_email != user.email.strip().lower():
            raise serializers.ValidationError(
                {
                    "credential": (
                        "The Google credential could not "
                        "be verified for this account."
                    )
                }
            )

        try:
            validate_password(
                attrs["password"],
                user=user,
            )
        except DjangoValidationError as exc:
            raise serializers.ValidationError({"password": list(exc.messages)})

        return attrs

    def create(self, validated_data):
        request_user = self.context["request"].user

        with transaction.atomic():
            user = User.objects.select_for_update().get(pk=request_user.pk)

            if user.has_usable_password():
                raise serializers.ValidationError(
                    {"non_field_errors": ("This account already has a password.")}
                )

            user.set_password(validated_data["password"])
            user.save(update_fields=["password"])

        return {"password_set": True}


class UsernameChangeSerializer(serializers.Serializer):
    username = serializers.RegexField(
        regex=r"^[A-Za-z0-9_]{3,30}$",
        max_length=30,
        error_messages={
            "invalid": (
                "Username must contain 3 to 30 letters, " "numbers or underscores."
            ),
        },
    )
    current_password = serializers.CharField(
        write_only=True,
        required=False,
        allow_blank=True,
        trim_whitespace=False,
    )

    def validate_username(self, value):
        return value.strip().lower()

    def create(self, validated_data):
        request_user = self.context["request"].user
        new_username = validated_data["username"]
        current_password = validated_data.get(
            "current_password",
            "",
        )
        now = timezone.now()

        try:
            with transaction.atomic():
                user = User.objects.select_for_update().get(pk=request_user.pk)

                if user.username.lower() == new_username:
                    raise serializers.ValidationError(
                        {"username": ("Choose a different username.")}
                    )

                if user.has_usable_password():
                    if not user.check_password(current_password):
                        raise serializers.ValidationError(
                            {"current_password": ("The password is incorrect.")}
                        )

                if user.username_changed_at is not None:
                    next_change_at = user.username_changed_at + timedelta(days=60)

                    if now < next_change_at:
                        raise serializers.ValidationError(
                            {
                                "username": (
                                    "Username can only be changed "
                                    "once every 60 days."
                                ),
                                "next_change_at": next_change_at,
                            }
                        )

                username_unavailable = (
                    User.objects.filter(username__iexact=new_username)
                    .exclude(pk=user.pk)
                    .exists()
                    or UsernameHistory.objects.filter(
                        old_username__iexact=new_username
                    ).exists()
                )

                if username_unavailable:
                    raise serializers.ValidationError(
                        {"username": ("This username is unavailable.")}
                    )

                old_username = user.username

                UsernameHistory.objects.create(
                    user=user,
                    old_username=old_username,
                    new_username=new_username,
                )

                user.username = new_username
                user.username_changed_at = now
                user.save(
                    update_fields=[
                        "username",
                        "username_changed_at",
                    ]
                )

        except IntegrityError as exc:
            raise serializers.ValidationError(
                {"username": ("This username is unavailable.")}
            ) from exc

        return {
            "username": user.username,
            "username_changed_at": (user.username_changed_at),
            "next_change_at": (user.username_changed_at + timedelta(days=60)),
        }
