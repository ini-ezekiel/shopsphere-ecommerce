from django.urls import path
from rest_framework_simplejwt.views import (
    TokenBlacklistView,
)

from .views import (
    AccountProfileView,
    EmailVerificationResendView,
    EmailVerificationView,
    LoginView,
    PasswordChangeView,
    PasswordResetConfirmView,
    PasswordResetRequestView,
    RefreshTokenView,
    GoogleAuthenticationView,
    RegistrationStartView,
    RegistrationVerifyView,
    RegistrationCompleteView,
    UsernameChangeView,
    GoogleAccountLinkView,
    GoogleAccountUnlinkView,
    GoogleSetPasswordView,
    api_health,
)

urlpatterns = [
    path("health/", api_health, name="api-health",),
    path("auth/login/", LoginView.as_view(), name="login",),
    path("auth/token/refresh/", RefreshTokenView.as_view(), name="token_refresh",),
    path("auth/logout/", TokenBlacklistView.as_view(), name="logout",),
    path("account/profile/", AccountProfileView.as_view(), name="account_profile",),
    path("auth/password/change/", PasswordChangeView.as_view(), name="password_change",),
    path("auth/email/verify/", EmailVerificationView.as_view(), name="email_verify",),
    path("auth/email/resend/", EmailVerificationResendView.as_view(), name="email_resend",),
    path("auth/password/reset/", PasswordResetRequestView.as_view(), name="password-reset",),
    path("auth/password/reset/confirm/", PasswordResetConfirmView.as_view(), name="password-reset-confirm",),
    path("auth/google/", GoogleAuthenticationView.as_view(), name="google-auth",),
    path("auth/register/start/", RegistrationStartView.as_view(), name="registration-start",),
    path("auth/register/verify/", RegistrationVerifyView.as_view(), name="registration-verify",),
    path("auth/register/complete/", RegistrationCompleteView.as_view(), name="registration-complete",),
    path("account/username/", UsernameChangeView.as_view(), name="username-change",),
    path("auth/google/link/", GoogleAccountLinkView.as_view(), name="google-link",),
    path("auth/google/unlink/", GoogleAccountUnlinkView.as_view(), name="google-unlink",),
    path("auth/google/password/set/", GoogleSetPasswordView.as_view(), name="google-set-password",),
]
