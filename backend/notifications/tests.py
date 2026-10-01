from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core import mail
from django.test import override_settings
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from orders.models import Order
from payments.models import Payment, Refund

from .models import Notification
from .services import NotificationError, create_notification

User = get_user_model()


@override_settings(
    NOTIFICATION_EMAILS_ENABLED=False,
)
class NotificationAPITests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="notification_user",
            email="notification@example.com",
            password="StrongPassword123!",
            is_email_verified=True,
        )

        self.other_user = User.objects.create_user(
            username="other_notification_user",
            email="other-notification@example.com",
            password="StrongPassword123!",
            is_email_verified=True,
        )

        self.list_url = reverse(
            "notifications:customer-notification-list",
        )

        self.unread_count_url = reverse(
            "notifications:customer-notification-unread-count",
        )

        self.mark_all_read_url = reverse(
            "notifications:customer-notification-mark-all-read",
        )

    def authenticate(self, user=None):
        self.client.force_authenticate(
            user=user or self.user,
        )

    def create_test_notification(
        self,
        *,
        user=None,
        event_type=Notification.EventType.ORDER_PROCESSING,
        suffix="default",
    ):
        user = user or self.user

        notification, _created = create_notification(
            user=user,
            event_type=event_type,
            title="Test notification",
            message="This is a test notification.",
            link="/account/orders/",
            metadata={
                "test": True,
            },
            deduplication_key=(f"notification-test:{user.pk}:{suffix}"),
        )

        return notification

    def create_order(self, user=None):
        user = user or self.user

        return Order.objects.create(
            user=user,
            status=Order.Status.PENDING_PAYMENT,
            inventory_status=(Order.InventoryStatus.NOT_RESERVED),
            recipient_name="Notification Customer",
            phone_number="08012345678",
            address_line_1="12 Notification Street",
            address_line_2="",
            landmark="",
            postal_code="520101",
            city="Uyo",
            state="Akwa Ibom",
            country="Nigeria",
            estimated_delivery_days=2,
            currency="NGN",
            subtotal=Decimal("1000.00"),
            discount_amount=Decimal("0.00"),
            shipping_fee=Decimal("0.00"),
            total_amount=Decimal("1000.00"),
        )

    def create_payment(
        self,
        *,
        order=None,
        payment_status=Payment.Status.INITIALIZED,
    ):
        order = order or self.create_order()

        return Payment.objects.create(
            order=order,
            status=payment_status,
            provider_status=(
                "success" if payment_status == Payment.Status.SUCCESSFUL else ""
            ),
            amount=order.total_amount,
            amount_subunit=100000,
            currency=order.currency,
            provider_transaction_id=(
                9000000000 + order.pk
                if payment_status == Payment.Status.SUCCESSFUL
                else None
            ),
        )

    def mark_read_url(self, notification):
        return reverse(
            "notifications:customer-notification-mark-read",
            args=[notification.pk],
        )

    def test_notification_list_requires_authentication(self):
        response = self.client.get(
            self.list_url,
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_401_UNAUTHORIZED,
        )

    def test_customer_lists_only_own_notifications(self):
        own_notification = self.create_test_notification(
            suffix="own",
        )

        self.create_test_notification(
            user=self.other_user,
            suffix="other",
        )

        self.authenticate()

        response = self.client.get(
            self.list_url,
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.assertEqual(
            response.data["count"],
            1,
        )

        self.assertEqual(
            response.data["results"][0]["id"],
            own_notification.id,
        )

    def test_unread_filter_returns_only_unread_notifications(self):
        read_notification = self.create_test_notification(
            suffix="read",
        )

        unread_notification = self.create_test_notification(
            suffix="unread",
        )

        from django.utils import timezone

        read_notification.read_at = timezone.now()
        read_notification.save(
            update_fields=[
                "read_at",
            ]
        )

        self.authenticate()

        response = self.client.get(
            self.list_url,
            {
                "unread": "true",
            },
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.assertEqual(
            response.data["count"],
            1,
        )

        self.assertEqual(
            response.data["results"][0]["id"],
            unread_notification.id,
        )

    def test_unread_count_returns_customer_total(self):
        self.create_test_notification(
            suffix="one",
        )

        self.create_test_notification(
            suffix="two",
        )

        self.create_test_notification(
            user=self.other_user,
            suffix="other",
        )

        self.authenticate()

        response = self.client.get(
            self.unread_count_url,
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.assertEqual(
            response.data["unread_count"],
            2,
        )

    def test_customer_can_mark_notification_as_read(self):
        notification = self.create_test_notification(
            suffix="mark-read",
        )

        self.authenticate()

        response = self.client.patch(
            self.mark_read_url(notification),
            {},
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.assertTrue(
            response.data["is_read"],
        )

        self.assertTrue(
            response.data["marked_read"],
        )

        notification.refresh_from_db()

        self.assertIsNotNone(
            notification.read_at,
        )

    def test_marking_notification_read_is_idempotent(self):
        notification = self.create_test_notification(
            suffix="idempotent-read",
        )

        self.authenticate()

        first_response = self.client.patch(
            self.mark_read_url(notification),
            {},
            format="json",
        )

        first_read_at = first_response.data["read_at"]

        second_response = self.client.patch(
            self.mark_read_url(notification),
            {},
            format="json",
        )

        self.assertTrue(
            first_response.data["marked_read"],
        )

        self.assertFalse(
            second_response.data["marked_read"],
        )

        self.assertEqual(
            second_response.data["read_at"],
            first_read_at,
        )

    def test_customer_cannot_mark_another_users_notification(self):
        notification = self.create_test_notification(
            user=self.other_user,
            suffix="ownership",
        )

        self.authenticate()

        response = self.client.patch(
            self.mark_read_url(notification),
            {},
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_404_NOT_FOUND,
        )

        notification.refresh_from_db()

        self.assertIsNone(
            notification.read_at,
        )

    def test_customer_can_mark_all_own_notifications_as_read(self):
        self.create_test_notification(
            suffix="all-one",
        )

        self.create_test_notification(
            suffix="all-two",
        )

        other_notification = self.create_test_notification(
            user=self.other_user,
            suffix="all-other",
        )

        self.authenticate()

        response = self.client.post(
            self.mark_all_read_url,
            {},
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.assertEqual(
            response.data["marked_read_count"],
            2,
        )

        self.assertEqual(
            Notification.objects.filter(
                user=self.user,
                read_at__isnull=True,
            ).count(),
            0,
        )

        other_notification.refresh_from_db()

        self.assertIsNone(
            other_notification.read_at,
        )

    def test_notification_creation_is_idempotent(self):
        first_notification, first_created = create_notification(
            user=self.user,
            event_type=Notification.EventType.ORDER_PROCESSING,
            title="Order processing",
            message="Your order is processing.",
            deduplication_key="service-idempotency-test",
        )

        second_notification, second_created = create_notification(
            user=self.user,
            event_type=Notification.EventType.ORDER_PROCESSING,
            title="Order processing",
            message="Your order is processing.",
            deduplication_key="service-idempotency-test",
        )

        self.assertTrue(first_created)
        self.assertFalse(second_created)

        self.assertEqual(
            first_notification.pk,
            second_notification.pk,
        )

        self.assertEqual(
            Notification.objects.filter(
                deduplication_key=("service-idempotency-test"),
            ).count(),
            1,
        )

    def test_invalid_notification_event_type_is_rejected(self):
        with self.assertRaises(NotificationError):
            create_notification(
                user=self.user,
                event_type="invalid-event",
                title="Invalid notification",
                message="This must not be created.",
                deduplication_key="invalid-event-test",
            )

        self.assertEqual(
            Notification.objects.count(),
            0,
        )

    def test_payment_success_signal_creates_notification_once(self):
        order = self.create_order()
        payment = self.create_payment(
            order=order,
        )

        payment.status = Payment.Status.SUCCESSFUL
        payment.provider_status = "success"
        payment.save(
            update_fields=[
                "status",
                "provider_status",
                "updated_at",
            ]
        )

        payment.save(
            update_fields=[
                "updated_at",
            ]
        )

        notifications = Notification.objects.filter(
            user=self.user,
            event_type=(Notification.EventType.PAYMENT_CONFIRMED),
        )

        self.assertEqual(
            notifications.count(),
            1,
        )

        self.assertEqual(
            notifications.get().metadata["payment_reference"],
            payment.reference,
        )

    def test_order_processing_signal_creates_notification_once(self):
        order = self.create_order()

        order.status = Order.Status.PROCESSING
        order.save(
            update_fields=[
                "status",
                "updated_at",
            ]
        )

        order.save(
            update_fields=[
                "updated_at",
            ]
        )

        notifications = Notification.objects.filter(
            user=self.user,
            event_type=(Notification.EventType.ORDER_PROCESSING),
        )

        self.assertEqual(
            notifications.count(),
            1,
        )

        self.assertEqual(
            notifications.get().metadata["order_number"],
            order.order_number,
        )

    def test_refund_pending_signal_creates_notification_once(self):
        order = self.create_order()
        payment = self.create_payment(
            order=order,
            payment_status=Payment.Status.SUCCESSFUL,
        )

        refund = Refund.objects.create(
            payment=payment,
            requested_by=self.other_user,
            requested_by_email=self.other_user.email,
            status=Refund.Status.INITIALIZED,
            amount=payment.amount,
            amount_subunit=payment.amount_subunit,
            currency=payment.currency,
            reason="Customer cancellation approved.",
        )

        refund.status = Refund.Status.PENDING
        refund.provider_status = "pending"
        refund.provider_refund_id = "refund-test-1"
        refund.save(
            update_fields=[
                "status",
                "provider_status",
                "provider_refund_id",
                "updated_at",
            ]
        )

        refund.save(
            update_fields=[
                "updated_at",
            ]
        )

        notifications = Notification.objects.filter(
            user=self.user,
            event_type=(Notification.EventType.REFUND_INITIATED),
        )

        self.assertEqual(
            notifications.count(),
            1,
        )

        self.assertEqual(
            notifications.get().metadata["refund_reference"],
            refund.reference,
        )

    @override_settings(
        NOTIFICATION_EMAILS_ENABLED=True,
        EMAIL_BACKEND=("django.core.mail.backends.locmem.EmailBackend"),
    )
    def test_created_notification_sends_email_once(self):
        with self.captureOnCommitCallbacks(
            execute=True,
        ):
            first_notification, first_created = create_notification(
                user=self.user,
                event_type=(Notification.EventType.ORDER_PROCESSING),
                title="Order processing",
                message="Your order is processing.",
                link="/account/orders/",
                deduplication_key="email-once-test",
                email_subject="Order processing",
            )

        with self.captureOnCommitCallbacks(
            execute=True,
        ):
            second_notification, second_created = create_notification(
                user=self.user,
                event_type=(Notification.EventType.ORDER_PROCESSING),
                title="Order processing",
                message="Your order is processing.",
                link="/account/orders/",
                deduplication_key="email-once-test",
                email_subject="Order processing",
            )

        self.assertTrue(first_created)
        self.assertFalse(second_created)

        self.assertEqual(
            first_notification.pk,
            second_notification.pk,
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
            "/account/orders/",
            mail.outbox[0].body,
        )
