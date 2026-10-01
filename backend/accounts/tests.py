from unittest.mock import patch
from django.contrib.auth import get_user_model
from django.core.cache import cache
from rest_framework import status
from rest_framework.test import APITestCase


from django.urls import reverse
from .models import SocialIdentity

from google.auth.exceptions import TransportError


from datetime import timedelta
from django.contrib.auth.hashers import check_password
from django.utils import timezone

from .models import PendingRegistration, UsernameHistory

from datetime import timedelta

from .models import UsernameHistory

from datetime import datetime

from django.contrib.auth.tokens import default_token_generator
from django.core import mail
from django.test import override_settings
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from rest_framework_simplejwt.tokens import RefreshToken

User = get_user_model()


class AuthenticationAPITests(APITestCase):
    def setUp(self):
        cache.clear()

        self.password = "StrongPassword123!"

        self.verified_user = User.objects.create_user(
            username="verifieduser",
            email="verified@example.com",
            password=self.password,
            is_email_verified=True,
        )

        self.unverified_user = User.objects.create_user(
            username="unverifieduser",
            email="unverified@example.com",
            password=self.password,
            is_email_verified=False,
        )

    def test_unverified_user_cannot_login(self):
        response = self.client.post(
            "/api/v1/auth/login/",
            {
                "email": self.unverified_user.email,
                "password": self.password,
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_401_UNAUTHORIZED,
        )

    def test_verified_user_can_login(self):
        response = self.client.post(
            "/api/v1/auth/login/",
            {
                "email": self.verified_user.email,
                "password": self.password,
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )
        self.assertIn("access", response.data)
        self.assertIn("refresh", response.data)

    def test_invalid_login_responses_are_generic(self):
        wrong_password_response = self.client.post(
            "/api/v1/auth/login/",
            {
                "email": self.verified_user.email,
                "password": "WrongPassword123!",
            },
            format="json",
        )

        unknown_email_response = self.client.post(
            "/api/v1/auth/login/",
            {
                "email": "unknown@example.com",
                "password": "WrongPassword123!",
            },
            format="json",
        )

        self.assertEqual(
            wrong_password_response.status_code,
            status.HTTP_401_UNAUTHORIZED,
        )
        self.assertEqual(
            unknown_email_response.status_code,
            status.HTTP_401_UNAUTHORIZED,
        )
        self.assertEqual(
            wrong_password_response.data,
            unknown_email_response.data,
        )

    def test_profile_requires_authentication(self):
        response = self.client.get("/api/v1/account/profile/")

        self.assertEqual(
            response.status_code,
            status.HTTP_401_UNAUTHORIZED,
        )

    def test_authenticated_user_can_view_own_profile(self):
        login_response = self.client.post(
            "/api/v1/auth/login/",
            {
                "email": self.verified_user.email,
                "password": self.password,
            },
            format="json",
        )

        access_token = login_response.data["access"]

        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {access_token}")

        response = self.client.get("/api/v1/account/profile/")

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )
        self.assertEqual(
            response.data["email"],
            self.verified_user.email,
        )


# GOOGLE AUTH TEST


class GoogleAuthenticationTests(APITestCase):
    def setUp(self):
        self.url = reverse("google-auth")
        self.google_payload = {
            "sub": "google-user-123",
            "email": "reborn@example.com",
            "email_verified": True,
            "given_name": "John",
            "family_name": "Doe",
        }

    @patch("accounts.serializers.verify_google_credential")
    def test_new_google_user_is_created(self, mock_verify):
        mock_verify.return_value = self.google_payload

        response = self.client.post(
            self.url,
            {"credential": "valid-google-token"},
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
        )
        self.assertTrue(response.data["is_new_user"])
        self.assertIn("access", response.data)
        self.assertIn("refresh", response.data)

        user = User.objects.get(email="reborn@example.com")

        self.assertEqual(user.first_name, "John")
        self.assertEqual(user.last_name, "Doe")
        self.assertTrue(user.is_email_verified)
        self.assertFalse(user.has_usable_password())
        self.assertRegex(
            user.username,
            r"^john_[a-z]{6}$",
        )

        self.assertTrue(
            SocialIdentity.objects.filter(
                user=user,
                provider=SocialIdentity.Provider.GOOGLE,
                subject="google-user-123",
            ).exists()
        )

    @patch("accounts.serializers.verify_google_credential")
    def test_existing_google_user_is_signed_in(
        self,
        mock_verify,
    ):
        mock_verify.return_value = self.google_payload

        first_response = self.client.post(
            self.url,
            {"credential": "valid-google-token"},
            format="json",
        )
        second_response = self.client.post(
            self.url,
            {"credential": "valid-google-token"},
            format="json",
        )

        self.assertEqual(
            first_response.status_code,
            status.HTTP_201_CREATED,
        )
        self.assertEqual(
            second_response.status_code,
            status.HTTP_200_OK,
        )
        self.assertFalse(second_response.data["is_new_user"])
        self.assertEqual(User.objects.count(), 1)
        self.assertEqual(
            SocialIdentity.objects.count(),
            1,
        )
        self.assertEqual(
            first_response.data["user"]["id"],
            second_response.data["user"]["id"],
        )
        self.assertEqual(
            first_response.data["user"]["username"],
            second_response.data["user"]["username"],
        )

    @patch("accounts.serializers.verify_google_credential")
    def test_existing_password_account_is_not_auto_linked(
        self,
        mock_verify,
    ):
        mock_verify.return_value = self.google_payload

        User.objects.create_user(
            username="john_local",
            email="reborn@example.com",
            password="StrongPassword123!",
        )

        response = self.client.post(
            self.url,
            {"credential": "valid-google-token"},
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )
        self.assertEqual(User.objects.count(), 1)
        self.assertEqual(
            SocialIdentity.objects.count(),
            0,
        )

    @patch("accounts.serializers.verify_google_credential")
    def test_invalid_google_credential_is_rejected(
        self,
        mock_verify,
    ):
        mock_verify.side_effect = ValueError("Invalid Google token")

        response = self.client.post(
            self.url,
            {"credential": "invalid-token"},
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )
        self.assertEqual(User.objects.count(), 0)
        self.assertEqual(
            SocialIdentity.objects.count(),
            0,
        )

    @patch("accounts.serializers.verify_google_credential")
    def test_google_transport_failure_returns_503(
        self,
        mock_verify,
    ):
        mock_verify.side_effect = TransportError("Google could not be reached")
        response = self.client.post(
            self.url,
            {"credential": "google-token"},
            format="json",
        )
        self.assertEqual(
            response.status_code,
            status.HTTP_503_SERVICE_UNAVAILABLE,
        )
        self.assertEqual(
            response.data["detail"],
            "Google authentication is temporarily unavailable.",
        )
        self.assertEqual(User.objects.count(), 0)


# OTP REGISTRATION TEST


class OTPRegistrationTests(APITestCase):
    def setUp(self):
        cache.clear()

        self.start_url = reverse("registration-start")
        self.verify_url = reverse("registration-verify")
        self.complete_url = reverse("registration-complete")

        self.email = "otpuser@example.com"

    def start_registration(self, otp="123456"):
        with patch(
            "accounts.serializers.generate_registration_otp",
            return_value=otp,
        ), patch("accounts.serializers.send_registration_otp") as mock_send:
            with self.captureOnCommitCallbacks(execute=True):
                response = self.client.post(
                    self.start_url,
                    {"email": self.email},
                    format="json",
                )

        return response, mock_send

    def verify_registration(
        self,
        registration_id,
        otp="123456",
    ):
        return self.client.post(
            self.verify_url,
            {
                "registration_id": registration_id,
                "otp": otp,
            },
            format="json",
        )

    def completion_payload(
        self,
        registration_id,
        registration_token,
    ):
        return {
            "registration_id": registration_id,
            "registration_token": registration_token,
            "first_name": "John",
            "last_name": "Doe",
            "username": "john_otp",
            "password": "StrongPassword123!",
            "password2": "StrongPassword123!",
        }

    def test_complete_registration_flow(self):
        start_response, mock_send = self.start_registration()

        self.assertEqual(
            start_response.status_code,
            status.HTTP_200_OK,
        )
        self.assertEqual(mock_send.call_count, 1)

        registration_id = start_response.data["registration_id"]

        pending = PendingRegistration.objects.get(id=registration_id)

        self.assertNotEqual(
            pending.otp_hash,
            "123456",
        )
        self.assertTrue(
            check_password(
                "123456",
                pending.otp_hash,
            )
        )

        verify_response = self.verify_registration(registration_id)

        self.assertEqual(
            verify_response.status_code,
            status.HTTP_200_OK,
        )

        registration_token = verify_response.data["registration_token"]

        complete_response = self.client.post(
            self.complete_url,
            self.completion_payload(
                registration_id,
                registration_token,
            ),
            format="json",
        )

        self.assertEqual(
            complete_response.status_code,
            status.HTTP_201_CREATED,
        )
        self.assertIn("access", complete_response.data)
        self.assertIn("refresh", complete_response.data)

        user = User.objects.get(email=self.email)

        self.assertEqual(user.username, "john_otp")
        self.assertEqual(user.first_name, "John")
        self.assertEqual(user.last_name, "Doe")
        self.assertTrue(user.is_email_verified)
        self.assertTrue(user.check_password("StrongPassword123!"))

        reuse_response = self.client.post(
            self.complete_url,
            self.completion_payload(
                registration_id,
                registration_token,
            ),
            format="json",
        )

        self.assertEqual(
            reuse_response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )
        self.assertEqual(
            User.objects.filter(email=self.email).count(),
            1,
        )

    def test_five_wrong_otps_block_correct_otp(self):
        start_response, _ = self.start_registration()
        registration_id = start_response.data["registration_id"]

        for _ in range(5):
            response = self.verify_registration(
                registration_id,
                otp="654321",
            )

            self.assertEqual(
                response.status_code,
                status.HTTP_400_BAD_REQUEST,
            )

        pending = PendingRegistration.objects.get(id=registration_id)
        self.assertEqual(pending.otp_attempts, 5)

        correct_response = self.verify_registration(
            registration_id,
            otp="123456",
        )

        self.assertEqual(
            correct_response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

    def test_expired_otp_is_rejected(self):
        start_response, _ = self.start_registration()
        registration_id = start_response.data["registration_id"]

        PendingRegistration.objects.filter(id=registration_id).update(
            otp_expires_at=(timezone.now() - timedelta(seconds=1))
        )

        response = self.verify_registration(
            registration_id,
            otp="123456",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

    def test_resend_invalidates_previous_otp(self):
        first_response, _ = self.start_registration(otp="123456")
        registration_id = first_response.data["registration_id"]

        PendingRegistration.objects.filter(id=registration_id).update(
            last_sent_at=(timezone.now() - timedelta(seconds=61))
        )

        second_response, second_mock_send = self.start_registration(otp="654321")

        self.assertEqual(
            second_response.data["registration_id"],
            registration_id,
        )
        self.assertEqual(
            second_mock_send.call_count,
            1,
        )

        old_otp_response = self.verify_registration(
            registration_id,
            otp="123456",
        )
        self.assertEqual(
            old_otp_response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

        new_otp_response = self.verify_registration(
            registration_id,
            otp="654321",
        )
        self.assertEqual(
            new_otp_response.status_code,
            status.HTTP_200_OK,
        )

    def test_expired_completion_token_is_rejected(self):
        start_response, _ = self.start_registration()
        registration_id = start_response.data["registration_id"]
        verify_response = self.verify_registration(registration_id)
        registration_token = verify_response.data["registration_token"]
        PendingRegistration.objects.filter(id=registration_id).update(
            completion_token_expires_at=(timezone.now() - timedelta(seconds=1))
        )
        response = self.client.post(
            self.complete_url,
            self.completion_payload(
                registration_id,
                registration_token,
            ),
            format="json",
        )
        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )
        self.assertFalse(User.objects.filter(email=self.email).exists())

    def test_existing_email_does_not_receive_otp(self):
        User.objects.create_user(
            username="existing_user",
            email=self.email,
            password="StrongPassword123!",
        )
        start_response, mock_send = self.start_registration()
        self.assertEqual(
            start_response.status_code,
            status.HTTP_200_OK,
        )
        self.assertEqual(mock_send.call_count, 0)
        registration_id = start_response.data["registration_id"]
        verify_response = self.verify_registration(
            registration_id,
            otp="123456",
        )
        self.assertEqual(
            verify_response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )
        self.assertEqual(
            User.objects.filter(email=self.email).count(),
            1,
        )

    def test_invalid_password_does_not_consume_token(self):
        start_response, _ = self.start_registration()
        registration_id = start_response.data["registration_id"]
        verify_response = self.verify_registration(registration_id)
        registration_token = verify_response.data["registration_token"]
        mismatched_payload = self.completion_payload(
            registration_id,
            registration_token,
        )
        mismatched_payload["password2"] = "DifferentPassword123!"
        mismatch_response = self.client.post(
            self.complete_url,
            mismatched_payload,
            format="json",
        )
        self.assertEqual(
            mismatch_response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )
        weak_payload = self.completion_payload(
            registration_id,
            registration_token,
        )
        weak_payload["password"] = "password"
        weak_payload["password2"] = "password"
        weak_response = self.client.post(
            self.complete_url,
            weak_payload,
            format="json",
        )
        self.assertEqual(
            weak_response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )
        valid_response = self.client.post(
            self.complete_url,
            self.completion_payload(
                registration_id,
                registration_token,
            ),
            format="json",
        )
        self.assertEqual(
            valid_response.status_code,
            status.HTTP_201_CREATED,
        )

    def test_current_and_previous_usernames_are_unavailable(
        self,
    ):
        owner = User.objects.create_user(
            username="current_name",
            email="owner@example.com",
            password="StrongPassword123!",
        )
        UsernameHistory.objects.create(
            user=owner,
            old_username="retired_name",
            new_username="current_name",
        )
        start_response, _ = self.start_registration()
        registration_id = start_response.data["registration_id"]
        verify_response = self.verify_registration(registration_id)
        registration_token = verify_response.data["registration_token"]
        current_payload = self.completion_payload(
            registration_id,
            registration_token,
        )
        current_payload["username"] = "current_name"
        current_response = self.client.post(
            self.complete_url,
            current_payload,
            format="json",
        )
        self.assertEqual(
            current_response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )
        retired_payload = self.completion_payload(
            registration_id,
            registration_token,
        )
        retired_payload["username"] = "retired_name"
        retired_response = self.client.post(
            self.complete_url,
            retired_payload,
            format="json",
        )
        self.assertEqual(
            retired_response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )
        available_payload = self.completion_payload(
            registration_id,
            registration_token,
        )
        available_payload["username"] = "available_name"
        available_response = self.client.post(
            self.complete_url,
            available_payload,
            format="json",
        )
        self.assertEqual(
            available_response.status_code,
            status.HTTP_201_CREATED,
        )


# USERNAME CHANGE API TEST

User = get_user_model()


class UsernameChangeAPITests(APITestCase):
    def setUp(self):
        cache.clear()
        self.password = "StrongPassword123!"
        self.user = User.objects.create_user(
            email="username@example.com",
            username="original_user",
            password=self.password,
            first_name="Original",
            last_name="User",
            is_email_verified=True,
        )
        self.url = reverse("username-change")

    def tearDown(self):
        cache.clear()

    def test_authentication_is_required(self):
        response = self.client.patch(
            self.url,
            {
                "username": "new_username",
                "current_password": self.password,
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_401_UNAUTHORIZED,
        )

    def test_rejects_incorrect_password(self):
        self.client.force_authenticate(self.user)

        response = self.client.patch(
            self.url,
            {
                "username": "new_username",
                "current_password": "WrongPassword123!",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

        self.user.refresh_from_db()
        self.assertEqual(
            self.user.username,
            "original_user",
        )

    def test_changes_username_and_records_history(self):
        self.client.force_authenticate(self.user)

        response = self.client.patch(
            self.url,
            {
                "username": "new_username",
                "current_password": self.password,
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.user.refresh_from_db()

        self.assertEqual(
            self.user.username,
            "new_username",
        )
        self.assertIsNotNone(self.user.username_changed_at)
        self.assertTrue(
            UsernameHistory.objects.filter(
                user=self.user,
                old_username="original_user",
                new_username="new_username",
            ).exists()
        )

    def test_rejects_change_during_cooldown(self):
        self.user.username_changed_at = timezone.now()
        self.user.save(update_fields=["username_changed_at"])
        self.client.force_authenticate(self.user)

        response = self.client.patch(
            self.url,
            {
                "username": "another_username",
                "current_password": self.password,
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )
        self.assertIn(
            "next_change_at",
            response.data,
        )

    def test_rejects_previously_used_username(self):
        UsernameHistory.objects.create(
            user=self.user,
            old_username="reserved_username",
            new_username=self.user.username,
        )
        self.user.username_changed_at = timezone.now() - timedelta(days=61)
        self.user.save(update_fields=["username_changed_at"])
        self.client.force_authenticate(self.user)

        response = self.client.patch(
            self.url,
            {
                "username": "reserved_username",
                "current_password": self.password,
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

    def test_user_without_password_can_change_username(self):
        self.user.set_unusable_password()
        self.user.save(update_fields=["password"])
        self.client.force_authenticate(self.user)

        response = self.client.patch(
            self.url,
            {
                "username": "google_username",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.user.refresh_from_db()
        self.assertEqual(
            self.user.username,
            "google_username",
        )


class GoogleAccountManagementTests(APITestCase):
    def setUp(self):
        cache.clear()

        self.password = "StrongPassword123!"
        self.user = User.objects.create_user(
            username="local_google_user",
            email="link@example.com",
            password=self.password,
            is_email_verified=True,
        )

        self.link_url = reverse("google-link")
        self.unlink_url = reverse("google-unlink")

        self.google_payload = {
            "sub": "google-link-subject",
            "email": self.user.email,
            "email_verified": True,
            "given_name": "Link",
            "family_name": "User",
        }

    def tearDown(self):
        cache.clear()

    def create_google_identity(self):
        return SocialIdentity.objects.create(
            user=self.user,
            provider=SocialIdentity.Provider.GOOGLE,
            subject=self.google_payload["sub"],
            email_at_link=self.user.email,
        )

    def test_link_and_unlink_require_authentication(self):
        link_response = self.client.post(
            self.link_url,
            {"credential": "google-token"},
            format="json",
        )

        unlink_response = self.client.delete(
            self.unlink_url,
            {"current_password": self.password},
            format="json",
        )

        self.assertEqual(
            link_response.status_code,
            status.HTTP_401_UNAUTHORIZED,
        )
        self.assertEqual(
            unlink_response.status_code,
            status.HTTP_401_UNAUTHORIZED,
        )

    @patch("accounts.serializers.verify_google_credential")
    def test_google_account_can_be_linked(
        self,
        mock_verify,
    ):
        mock_verify.return_value = self.google_payload
        self.client.force_authenticate(self.user)

        response = self.client.post(
            self.link_url,
            {"credential": "google-token"},
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
        )
        self.assertTrue(
            SocialIdentity.objects.filter(
                user=self.user,
                provider=SocialIdentity.Provider.GOOGLE,
                subject=self.google_payload["sub"],
            ).exists()
        )

    @patch("accounts.serializers.verify_google_credential")
    def test_google_email_must_match_user_email(
        self,
        mock_verify,
    ):
        payload = self.google_payload.copy()
        payload["email"] = "different@example.com"
        mock_verify.return_value = payload
        self.client.force_authenticate(self.user)

        response = self.client.post(
            self.link_url,
            {"credential": "google-token"},
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )
        self.assertFalse(
            SocialIdentity.objects.filter(
                user=self.user,
            ).exists()
        )

    @patch("accounts.serializers.verify_google_credential")
    def test_linking_same_google_account_is_idempotent(
        self,
        mock_verify,
    ):
        mock_verify.return_value = self.google_payload
        self.create_google_identity()
        self.client.force_authenticate(self.user)

        response = self.client.post(
            self.link_url,
            {"credential": "google-token"},
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )
        self.assertEqual(
            SocialIdentity.objects.filter(
                user=self.user,
            ).count(),
            1,
        )

    def test_wrong_password_does_not_unlink_google(self):
        self.create_google_identity()
        self.client.force_authenticate(self.user)

        response = self.client.delete(
            self.unlink_url,
            {"current_password": "WrongPassword123!"},
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )
        self.assertTrue(
            SocialIdentity.objects.filter(
                user=self.user,
            ).exists()
        )

    def test_google_account_can_be_unlinked(self):
        self.create_google_identity()
        self.client.force_authenticate(self.user)

        response = self.client.delete(
            self.unlink_url,
            {"current_password": self.password},
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )
        self.assertFalse(
            SocialIdentity.objects.filter(
                user=self.user,
            ).exists()
        )

    def test_google_only_user_cannot_unlink(self):
        self.user.set_unusable_password()
        self.user.save(update_fields=["password"])
        self.create_google_identity()
        self.client.force_authenticate(self.user)

        response = self.client.delete(
            self.unlink_url,
            {"current_password": ""},
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )
        self.assertTrue(
            SocialIdentity.objects.filter(
                user=self.user,
            ).exists()
        )


class GooglePasswordAndProfileTests(APITestCase):
    def setUp(self):
        cache.clear()

        self.user = User.objects.create_user(
            username="google_only_user",
            email="googleonly@example.com",
            password="TemporaryPassword123!",
            is_email_verified=True,
        )

        self.google_payload = {
            "sub": "google-only-subject",
            "email": self.user.email,
            "email_verified": True,
            "given_name": "Google",
            "family_name": "User",
        }

        self.set_password_url = reverse("google-set-password")
        self.profile_url = "/api/v1/account/profile/"

    def tearDown(self):
        cache.clear()

    def make_google_only(self):
        self.user.set_unusable_password()
        self.user.save(update_fields=["password"])

        SocialIdentity.objects.create(
            user=self.user,
            provider=SocialIdentity.Provider.GOOGLE,
            subject=self.google_payload["sub"],
            email_at_link=self.user.email,
        )

    @patch("accounts.serializers.verify_google_credential")
    def test_google_only_user_can_set_password(
        self,
        mock_verify,
    ):
        self.make_google_only()
        mock_verify.return_value = self.google_payload
        self.client.force_authenticate(self.user)

        response = self.client.post(
            self.set_password_url,
            {
                "credential": "google-token",
                "password": "NewStrongPassword123!",
                "password2": "NewStrongPassword123!",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("NewStrongPassword123!"))

    @patch("accounts.serializers.verify_google_credential")
    def test_existing_password_cannot_be_replaced(
        self,
        mock_verify,
    ):
        self.client.force_authenticate(self.user)

        response = self.client.post(
            self.set_password_url,
            {
                "credential": "google-token",
                "password": "ReplacementPassword123!",
                "password2": "ReplacementPassword123!",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )
        mock_verify.assert_not_called()

    @patch("accounts.serializers.verify_google_credential")
    def test_wrong_google_identity_cannot_set_password(
        self,
        mock_verify,
    ):
        self.make_google_only()

        wrong_payload = self.google_payload.copy()
        wrong_payload["sub"] = "another-google-subject"
        mock_verify.return_value = wrong_payload

        self.client.force_authenticate(self.user)

        response = self.client.post(
            self.set_password_url,
            {
                "credential": "wrong-google-token",
                "password": "NewStrongPassword123!",
                "password2": "NewStrongPassword123!",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

        self.user.refresh_from_db()
        self.assertFalse(self.user.has_usable_password())

    def test_profile_reports_authentication_methods(self):
        SocialIdentity.objects.create(
            user=self.user,
            provider=SocialIdentity.Provider.GOOGLE,
            subject=self.google_payload["sub"],
            email_at_link=self.user.email,
        )
        self.client.force_authenticate(self.user)

        response = self.client.get(self.profile_url)

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )
        self.assertTrue(response.data["has_password"])
        self.assertTrue(response.data["google_linked"])

    def test_profile_cannot_bypass_username_flow(self):
        original_username = self.user.username
        self.client.force_authenticate(self.user)

        response = self.client.patch(
            self.profile_url,
            {
                "username": "bypass_attempt",
                "first_name": "Updated",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.user.refresh_from_db()
        self.assertEqual(
            self.user.username,
            original_username,
        )
        self.assertEqual(
            self.user.first_name,
            "Updated",
        )


# password reset test
@override_settings(
    PASSWORD_RESET_TIMEOUT=3600,
    MAILERS={
        "default": {
            "BACKEND": ("django.core.mail.backends.locmem.EmailBackend"),
            "OPTIONS": {},
        },
    },
)
class PasswordResetAPITests(APITestCase):
    def setUp(self):
        cache.clear()

        self.old_password = "OldStrongPassword123!"
        self.new_password = "NewStrongPassword456!"

        self.user = User.objects.create_user(
            username="password_reset_user",
            email="password-reset@example.com",
            password=self.old_password,
            is_email_verified=True,
            is_active=True,
        )

        self.request_url = reverse(
            "password-reset",
        )

        self.confirm_url = reverse(
            "password-reset-confirm",
        )

        self.profile_url = reverse(
            "account_profile",
        )

        self.refresh_url = reverse(
            "token_refresh",
        )

    def tearDown(self):
        cache.clear()

    def request_reset(self, email=None):
        return self.client.post(
            self.request_url,
            {
                "email": email or self.user.email,
            },
            format="json",
        )

    def reset_credentials(self):
        uid = urlsafe_base64_encode(
            force_bytes(self.user.pk),
        )

        token = default_token_generator.make_token(
            self.user,
        )

        return uid, token

    def confirm_reset(
        self,
        *,
        uid=None,
        token=None,
        new_password=None,
        new_password2=None,
    ):
        generated_uid, generated_token = self.reset_credentials()

        return self.client.post(
            self.confirm_url,
            {
                "uid": uid or generated_uid,
                "token": token or generated_token,
                "new_password": (new_password or self.new_password),
                "new_password2": (new_password2 or self.new_password),
            },
            format="json",
        )

    def test_existing_account_receives_reset_email(self):
        response = self.request_reset()

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.assertEqual(
            response.data["detail"],
            (
                "If an account exists for this email, "
                "password reset instructions will be sent."
            ),
        )

        self.assertEqual(
            len(mail.outbox),
            1,
        )

        self.assertEqual(
            mail.outbox[0].to,
            [self.user.email],
        )

        self.assertIn(
            "UID:",
            mail.outbox[0].body,
        )

        self.assertIn(
            "Token:",
            mail.outbox[0].body,
        )

        self.assertIn(
            "/reset-password#uid=",
            mail.outbox[0].body,
        )

    def test_unknown_email_uses_generic_response(self):
        response = self.request_reset(
            "unknown@example.com",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.assertEqual(
            response.data["detail"],
            (
                "If an account exists for this email, "
                "password reset instructions will be sent."
            ),
        )

        self.assertEqual(
            len(mail.outbox),
            0,
        )

    def test_account_without_usable_password_gets_no_email(
        self,
    ):
        self.user.set_unusable_password()
        self.user.save(
            update_fields=[
                "password",
            ]
        )

        response = self.request_reset()

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.assertEqual(
            len(mail.outbox),
            0,
        )

    def test_valid_token_resets_password_once(self):
        uid, token = self.reset_credentials()

        first_response = self.confirm_reset(
            uid=uid,
            token=token,
        )

        self.assertEqual(
            first_response.status_code,
            status.HTTP_200_OK,
        )

        self.user.refresh_from_db()

        self.assertTrue(
            self.user.check_password(
                self.new_password,
            )
        )

        self.assertFalse(
            self.user.check_password(
                self.old_password,
            )
        )

        second_response = self.confirm_reset(
            uid=uid,
            token=token,
            new_password="AnotherStrongPassword789!",
            new_password2="AnotherStrongPassword789!",
        )

        self.assertEqual(
            second_response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

        self.user.refresh_from_db()

        self.assertTrue(
            self.user.check_password(
                self.new_password,
            )
        )

    def test_mismatched_passwords_do_not_reset_password(self):
        uid, token = self.reset_credentials()

        response = self.confirm_reset(
            uid=uid,
            token=token,
            new_password="FirstStrongPassword456!",
            new_password2="DifferentStrongPassword789!",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

        self.assertIn(
            "new_password2",
            response.data,
        )

        self.user.refresh_from_db()

        self.assertTrue(
            self.user.check_password(
                self.old_password,
            )
        )

    def test_invalid_uid_and_token_are_rejected(self):
        invalid_uid_response = self.confirm_reset(
            uid="invalid-uid",
            token="invalid-token",
        )

        self.assertEqual(
            invalid_uid_response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

        uid, _token = self.reset_credentials()

        invalid_token_response = self.confirm_reset(
            uid=uid,
            token="invalid-token",
        )

        self.assertEqual(
            invalid_token_response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

        self.user.refresh_from_db()

        self.assertTrue(
            self.user.check_password(
                self.old_password,
            )
        )

    def test_expired_token_is_rejected(self):
        issued_at = datetime.now()

        with patch.object(
            default_token_generator,
            "_now",
            return_value=issued_at,
        ):
            uid, token = self.reset_credentials()

        expired_time = issued_at + timedelta(
            seconds=3601,
        )

        with patch.object(
            default_token_generator,
            "_now",
            return_value=expired_time,
        ):
            response = self.confirm_reset(
                uid=uid,
                token=token,
            )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

        self.user.refresh_from_db()

        self.assertTrue(
            self.user.check_password(
                self.old_password,
            )
        )

    def test_password_reset_revokes_existing_jwts(self):
        refresh = RefreshToken.for_user(
            self.user,
        )

        old_refresh_token = str(refresh)
        old_access_token = str(refresh.access_token)

        uid, token = self.reset_credentials()

        response = self.confirm_reset(
            uid=uid,
            token=token,
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.client.credentials(HTTP_AUTHORIZATION=(f"Bearer {old_access_token}"))

        profile_response = self.client.get(
            self.profile_url,
        )

        self.assertEqual(
            profile_response.status_code,
            status.HTTP_401_UNAUTHORIZED,
        )

        self.client.credentials()

        refresh_response = self.client.post(
            self.refresh_url,
            {
                "refresh": old_refresh_token,
            },
            format="json",
        )

        self.assertEqual(
            refresh_response.status_code,
            status.HTTP_401_UNAUTHORIZED,
        )

    def test_password_reset_request_is_throttled(self):
        for _attempt in range(5):
            response = self.request_reset(
                "unknown@example.com",
            )

            self.assertEqual(
                response.status_code,
                status.HTTP_200_OK,
            )

        blocked_response = self.request_reset(
            "unknown@example.com",
        )

        self.assertEqual(
            blocked_response.status_code,
            status.HTTP_429_TOO_MANY_REQUESTS,
        )
