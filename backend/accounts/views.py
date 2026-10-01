from django.contrib.auth import get_user_model
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from .services import send_password_reset_email, send_verification_email
from django.db import transaction
from django.utils import timezone
from rest_framework_simplejwt.token_blacklist.models import (
    BlacklistedToken,
    OutstandingToken,
)

from .serializers import (
    AccountProfileSerializer,
    EmailVerificationResendSerializer,
    EmailVerificationSerializer,
    LoginSerializer,
    PasswordChangeSerializer,
    PasswordResetRequestSerializer,
    PasswordResetConfirmSerializer,
    GoogleAuthenticationSerializer,
    RegistrationStartSerializer,
    RegistrationVerifySerializer,
    RegistrationCompleteSerializer,
    UsernameChangeSerializer,
    GoogleAccountLinkSerializer,
    GoogleAccountUnlinkSerializer,
    GoogleSetPasswordSerializer,
)
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from rest_framework.generics import RetrieveUpdateAPIView
from .serializers import GoogleAuthenticationSerializer

from rest_framework import status

User = get_user_model()


@api_view(["GET"])
@permission_classes([AllowAny])
def api_health(request):
    return Response(
        {
            "status": "ok",
            "message": "E-commerce API is running.",
        }
    )


class LoginView(TokenObtainPairView):
    throttle_scope = "login"
    serializer_class = LoginSerializer


class AccountProfileView(RetrieveUpdateAPIView):
    serializer_class = AccountProfileSerializer

    def get_object(self):
        return self.request.user


# REGISTRATION TIMER (EXPIRES AFTER 24HRS)


class RegistrationStartView(APIView):
    permission_classes = [AllowAny]
    throttle_scope = "registration_start"

    def post(self, request):
        serializer = RegistrationStartSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        result = serializer.save()

        return Response(
            {
                "detail": (
                    "If this email can be registered, "
                    "a verification code has been sent."
                ),
                "registration_id": result["registration_id"],
            },
            status=status.HTTP_200_OK,
        )


# REGISTRATION VERIFICATION


class RegistrationVerifyView(APIView):
    permission_classes = [AllowAny]
    throttle_scope = "registration_verify"

    def post(self, request):
        serializer = RegistrationVerifySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        result = serializer.save()

        return Response(
            {
                "detail": ("Email verified. Complete your " "registration."),
                "registration_token": result["registration_token"],
                "expires_in_minutes": result["expires_in_minutes"],
            },
            status=status.HTTP_200_OK,
        )


# REGISTRATION COMPLETE


class RegistrationCompleteView(APIView):
    permission_classes = [AllowAny]
    throttle_scope = "registration_complete"

    def post(self, request):
        serializer = RegistrationCompleteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        result = serializer.save()

        return Response(
            {
                "detail": ("Registration completed successfully."),
                **result,
            },
            status=status.HTTP_201_CREATED,
        )


class PasswordChangeView(APIView):
    def post(self, request):
        serializer = PasswordChangeSerializer(
            data=request.data,
            context={"request": request},
        )

        serializer.is_valid(raise_exception=True)

        with transaction.atomic():
            serializer.save()

            active_refresh_tokens = OutstandingToken.objects.filter(
                user=request.user,
                expires_at__gt=timezone.now(),
            )

            for token in active_refresh_tokens:
                BlacklistedToken.objects.get_or_create(token=token)

        return Response(
            {"detail": ("Password changed successfully. " "Please log in again.")}
        )


class EmailVerificationView(APIView):
    permission_classes = [AllowAny]
    throttle_scope = "email_verify"

    def post(self, request):
        serializer = EmailVerificationSerializer(
            data=request.data,
        )

        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response({"detail": "Email verified successfully."})


class EmailVerificationResendView(APIView):
    permission_classes = [AllowAny]
    throttle_scope = "email_resend"

    def post(self, request):
        serializer = EmailVerificationResendSerializer(
            data=request.data,
        )

        serializer.is_valid(raise_exception=True)

        user = User.objects.filter(
            email__iexact=serializer.validated_data["email"],
        ).first()

        if user is not None and not user.is_email_verified:
            send_verification_email(user)

        return Response(
            {
                "detail": (
                    "If an eligible account exists, "
                    "a verification email has been sent."
                )
            }
        )


class PasswordResetRequestView(APIView):
    permission_classes = [AllowAny]
    throttle_scope = "password_reset"

    def post(self, request):
        serializer = PasswordResetRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        email = serializer.validated_data["email"]

        user = User.objects.filter(
            email__iexact=email,
            is_active=True,
        ).first()

        if user and user.has_usable_password():
            send_password_reset_email(user)

        return Response(
            {
                "detail": (
                    "If an account exists for this email, "
                    "password reset instructions will be sent."
                )
            },
            status=status.HTTP_200_OK,
        )


class PasswordResetConfirmView(APIView):
    permission_classes = [AllowAny]
    throttle_scope = "password_reset_confirm"

    def post(self, request):
        serializer = PasswordResetConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(
            {
                "detail": (
                    "Password reset successfully. "
                    "Please log in with your new password."
                )
            },
            status=status.HTTP_200_OK,
        )


class RefreshTokenView(TokenRefreshView):
    throttle_scope = "token_refresh"


class GoogleAuthenticationView(APIView):
    permission_classes = [AllowAny]
    throttle_scope = "google_auth"

    def post(self, request):
        serializer = GoogleAuthenticationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        response_data = serializer.validated_data
        response_status = (
            status.HTTP_201_CREATED
            if response_data["is_new_user"]
            else status.HTTP_200_OK
        )

        return Response(
            response_data,
            status=response_status,
        )


# GOOGLE ACCOUNT VIEW


class GoogleAccountLinkView(APIView):
    permission_classes = [IsAuthenticated]
    throttle_scope = "google_link"

    def post(self, request):
        serializer = GoogleAccountLinkSerializer(
            data=request.data,
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)

        already_linked = serializer.validated_data["already_linked"]

        return Response(
            {
                "detail": (
                    "Google account was already linked."
                    if already_linked
                    else "Google account linked successfully."
                ),
                "linked": True,
            },
            status=(status.HTTP_200_OK if already_linked else status.HTTP_201_CREATED),
        )


class GoogleAccountUnlinkView(APIView):
    permission_classes = [IsAuthenticated]
    throttle_scope = "google_unlink"

    def delete(self, request):
        serializer = GoogleAccountUnlinkSerializer(
            data=request.data,
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(
            {
                "detail": ("Google account unlinked successfully."),
                "linked": False,
            },
            status=status.HTTP_200_OK,
        )


class GoogleSetPasswordView(APIView):
    permission_classes = [IsAuthenticated]
    throttle_scope = "google_set_password"

    def post(self, request):
        serializer = GoogleSetPasswordSerializer(
            data=request.data,
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(
            {
                "detail": (
                    "Password created successfully. "
                    "Sign in again using Google or your "
                    "new password."
                ),
                "password_set": True,
            },
            status=status.HTTP_200_OK,
        )


# USERNAME CHNAGE FLOW


class UsernameChangeView(APIView):
    permission_classes = [IsAuthenticated]
    throttle_scope = "username_change"

    def patch(self, request):
        serializer = UsernameChangeSerializer(
            data=request.data,
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)

        result = serializer.save()

        return Response(
            {
                "detail": "Username changed successfully.",
                **result,
            },
            status=status.HTTP_200_OK,
        )
