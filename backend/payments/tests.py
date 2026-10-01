import hashlib

import hmac

import json

import uuid

from datetime import timedelta

from decimal import Decimal

from io import StringIO

from unittest.mock import patch


from django.contrib.auth import get_user_model

from django.core.cache import cache

from django.core.management import call_command

from django.test import override_settings

from django.urls import reverse

from django.utils import timezone

from rest_framework import status

from rest_framework.test import APITestCase


from addresses.models import (
    DeliveryLocation,
    ShippingAddress,
)

from carts.models import Cart, CartItem

from orders.models import Order

from products.models import (
    Brand,
    Category,
    Inventory,
    Product,
    ProductVariant,
)


from .models import Payment, Refund, WebhookEvent
from .paystack import PaystackAPIError

User = get_user_model()


@override_settings(
    PAYSTACK_SECRET_KEY="payment-test-secret",
)
class PaymentAPITests(APITestCase):

    def setUp(self):

        cache.clear()

        self.user = User.objects.create_user(
            username="payment_user",
            email="payment@example.com",
            password="StrongPassword123!",
            is_email_verified=True,
        )

        self.other_user = User.objects.create_user(
            username="other_payment_user",
            email="otherpayment@example.com",
            password="StrongPassword123!",
            is_email_verified=True,
        )

        self.staff_user = User.objects.create_user(
            username="payment_staff",
            email="payment-staff@example.com",
            password="StrongPassword123!",
            is_email_verified=True,
            is_staff=True,
            is_active=True,
        )

        self.brand = Brand.objects.create(
            name="Puma",
            slug="payment-puma",
            is_active=True,
        )

        self.category = Category.objects.create(
            name="Payment Sneakers",
            slug="payment-sneakers",
            description="Sneakers used for payment tests.",
            is_active=True,
        )

        self.product = Product.objects.create(
            category=self.category,
            brand=self.brand,
            name="Payment Test Sneaker",
            slug="payment-test-sneaker",
            description="A product used for payment tests.",
            is_active=True,
        )

        self.variant = ProductVariant.objects.create(
            product=self.product,
            name="White / Size 42",
            sku="PAYMENT-PUMA-WHT-42",
            attributes={
                "size": "42",
                "color": "White",
            },
            price=Decimal("40000.00"),
            is_active=True,
        )

        self.inventory = Inventory.objects.create(
            variant=self.variant,
            quantity=10,
            reserved_quantity=0,
        )

        self.location = DeliveryLocation.objects.create(
            state="Akwa Ibom",
            city="Uyo",
            shipping_fee=Decimal("2500.00"),
            estimated_delivery_days=2,
            is_active=True,
        )

        self.address = ShippingAddress.objects.create(
            user=self.user,
            delivery_location=self.location,
            label="home",
            recipient_name="Payment Customer",
            phone_number="08012345678",
            address_line_1="12 Payment Street",
            address_line_2="",
            landmark="Near Payment Junction",
            postal_code="520101",
            is_default=True,
        )

        self.other_address = ShippingAddress.objects.create(
            user=self.other_user,
            delivery_location=self.location,
            label="home",
            recipient_name="Other Payment Customer",
            phone_number="08098765432",
            address_line_1="10 Other Payment Street",
            address_line_2="",
            landmark="",
            postal_code="520102",
            is_default=True,
        )

        self.checkout_url = reverse(
            "orders:checkout",
        )

        self.webhook_url = reverse(
            "payments:paystack-webhook",
        )

    def tearDown(self):

        cache.clear()

    def authenticate(self, user=None):

        self.client.force_authenticate(
            user=user or self.user,
        )

    def create_order(
        self,
        *,
        user=None,
        address=None,
        quantity=1,
    ):

        user = user or self.user

        address = address or self.address

        cart, _created = Cart.objects.get_or_create(
            user=user,
        )

        CartItem.objects.create(
            cart=cart,
            variant=self.variant,
            quantity=quantity,
        )

        self.authenticate(user)

        response = self.client.post(
            self.checkout_url,
            {
                "idempotency_key": str(uuid.uuid4()),
                "shipping_address_id": address.id,
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
        )

        return Order.objects.get(
            pk=response.data["id"],
        )

    def payment_initialize_url(self, order):

        return reverse(
            "payments:payment-initialize",
            args=[order.order_number],
        )

    def payment_verify_url(self, payment):

        return reverse(
            "payments:payment-verify",
            args=[payment.reference],
        )

    def paystack_initialization_response(
        self,
        **request_data,
    ):

        reference = request_data["reference"]

        return {
            "status": True,
            "message": "Authorization URL created",
            "data": {
                "authorization_url": ("https://checkout.paystack.com/" f"{reference}"),
                "access_code": f"ACCESS-{reference}",
                "reference": reference,
            },
        }

    def paystack_verification_response(
        self,
        payment,
        *,
        provider_status="success",
        amount=None,
        paid_at=None,
        transaction_id=123456789,
    ):

        return {
            "status": True,
            "message": "Verification successful",
            "data": {
                "id": transaction_id,
                "status": provider_status,
                "reference": payment.reference,
                "amount": (payment.amount_subunit if amount is None else amount),
                "currency": payment.currency,
                "paid_at": (paid_at or timezone.now()).isoformat(),
                "channel": "card",
                "gateway_response": "Successful",
            },
        }

    def initialize_payment(
        self,
        order,
        *,
        idempotency_key=None,
    ):

        payment_key = idempotency_key or uuid.uuid4()

        self.authenticate(order.user)

        with patch("payments.services.initialize_transaction") as mocked_initialize:

            mocked_initialize.side_effect = self.paystack_initialization_response

            response = self.client.post(
                self.payment_initialize_url(order),
                {
                    "idempotency_key": str(payment_key),
                },
                format="json",
            )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
        )

        payment = Payment.objects.get(
            pk=response.data["id"],
        )

        return payment, response, payment_key

    def webhook_signature(self, raw_body):

        return hmac.new(
            b"payment-test-secret",
            raw_body,
            hashlib.sha512,
        ).hexdigest()

    def post_webhook(
        self,
        payload,
        *,
        signature=None,
    ):

        raw_body = json.dumps(
            payload,
            separators=(",", ":"),
        ).encode("utf-8")

        webhook_signature = (
            signature if signature is not None else self.webhook_signature(raw_body)
        )

        response = self.client.generic(
            "POST",
            self.webhook_url,
            raw_body,
            content_type="application/json",
            HTTP_X_PAYSTACK_SIGNATURE=(webhook_signature),
        )

        return response, raw_body

    def create_successful_payment(
        self,
        *,
        user=None,
        address=None,
    ):

        user = user or self.user

        address = address or self.address

        order = self.create_order(
            user=user,
            address=address,
        )

        order.status = Order.Status.CONFIRMED

        order.inventory_status = Order.InventoryStatus.COMMITTED

        order.save(
            update_fields=[
                "status",
                "inventory_status",
                "updated_at",
            ]
        )

        self.inventory.refresh_from_db()

        self.inventory.quantity -= 1

        self.inventory.reserved_quantity -= 1

        self.inventory.save(
            update_fields=[
                "quantity",
                "reserved_quantity",
                "updated_at",
            ]
        )

        provider_transaction_id = (uuid.uuid4().int % 9_000_000_000) + 1_000_000_000

        payment = Payment.objects.create(
            order=order,
            status=Payment.Status.SUCCESSFUL,
            provider_status="success",
            amount=order.total_amount,
            amount_subunit=4250000,
            currency=order.currency,
            provider_transaction_id=(provider_transaction_id),
            channel="card",
            gateway_response="Successful",
            paid_at=timezone.now(),
            verified_at=timezone.now(),
        )

        return order, payment

    def staff_refund_url(self, payment):

        return reverse(
            "payments:staff-refund-initiate",
            args=[payment.reference],
        )

    def customer_refund_list_url(self):

        return reverse(
            "payments:customer-refund-list",
        )

    def customer_refund_detail_url(self, refund):

        return reverse(
            "payments:customer-refund-detail",
            args=[refund.reference],
        )

    def paystack_refund_response(
        self,
        payment,
        *,
        provider_status="pending",
        provider_refund_id="987654321",
    ):

        return {
            "status": True,
            "message": "Refund created",
            "data": {
                "id": provider_refund_id,
                "status": provider_status,
                "amount": payment.amount_subunit,
                "currency": payment.currency,
                "transaction": {
                    "reference": payment.reference,
                },
            },
        }

    def initialize_refund(
        self,
        payment,
        *,
        reason="Customer cancellation approved before dispatch.",
    ):

        self.authenticate(self.staff_user)

        with patch(
            "payments.services.create_paystack_refund",
            return_value=self.paystack_refund_response(payment),
        ) as mocked_refund:

            response = self.client.post(
                self.staff_refund_url(payment),
                {
                    "reason": reason,
                },
                format="json",
            )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
        )

        refund = Refund.objects.get(
            pk=response.data["id"],
        )

        return refund, response, mocked_refund

    def refund_webhook_payload(
        self,
        refund,
        event_type,
        *,
        data_status=None,
        reason="",
    ):

        provider_status = data_status or event_type.removeprefix("refund.")

        payload = {
            "event": event_type,
            "data": {
                "id": refund.provider_refund_id,
                "status": provider_status,
                "amount": refund.amount_subunit,
                "currency": refund.currency,
                "transaction": {
                    "reference": refund.payment.reference,
                },
            },
        }

        if reason:

            payload["data"]["reason"] = reason

        return payload

    def test_payment_initialization_requires_authentication(
        self,
    ):

        order = self.create_order()

        self.client.force_authenticate(user=None)

        response = self.client.post(
            self.payment_initialize_url(order),
            {
                "idempotency_key": str(uuid.uuid4()),
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_401_UNAUTHORIZED,
        )

        self.assertEqual(
            Payment.objects.count(),
            0,
        )

    def test_unverified_user_cannot_initialize_payment(
        self,
    ):

        order = self.create_order()

        self.user.is_email_verified = False

        self.user.save(
            update_fields=[
                "is_email_verified",
            ]
        )

        self.authenticate(self.user)

        response = self.client.post(
            self.payment_initialize_url(order),
            {
                "idempotency_key": str(uuid.uuid4()),
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_403_FORBIDDEN,
        )

        self.assertEqual(
            Payment.objects.count(),
            0,
        )

    def test_user_cannot_initialize_another_users_payment(
        self,
    ):

        order = self.create_order(
            user=self.other_user,
            address=self.other_address,
        )

        self.authenticate(self.user)

        response = self.client.post(
            self.payment_initialize_url(order),
            {
                "idempotency_key": str(uuid.uuid4()),
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_404_NOT_FOUND,
        )

        self.assertEqual(
            Payment.objects.count(),
            0,
        )

    def test_successful_payment_initialization(
        self,
    ):

        order = self.create_order()

        self.authenticate()

        with patch("payments.services.initialize_transaction") as mocked_initialize:

            mocked_initialize.side_effect = self.paystack_initialization_response

            response = self.client.post(
                self.payment_initialize_url(order),
                {
                    "idempotency_key": str(uuid.uuid4()),
                },
                format="json",
            )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
        )

        self.assertEqual(
            response.data["status"],
            Payment.Status.PENDING,
        )

        self.assertEqual(
            response.data["amount"],
            "42500.00",
        )

        self.assertEqual(
            response.data["amount_subunit"],
            4250000,
        )

        self.assertTrue(
            response.data["authorization_url"],
        )

        self.assertTrue(
            response.data["access_code"],
        )

        payment = Payment.objects.get(
            pk=response.data["id"],
        )

        self.assertEqual(
            payment.order,
            order,
        )

        self.assertEqual(
            payment.status,
            Payment.Status.PENDING,
        )

        mocked_initialize.assert_called_once()

        call_data = mocked_initialize.call_args.kwargs

        self.assertEqual(
            call_data["email"],
            self.user.email,
        )

        self.assertEqual(
            call_data["amount_subunit"],
            4250000,
        )

        self.assertEqual(
            call_data["reference"],
            payment.reference,
        )

    def test_payment_initialization_is_idempotent(
        self,
    ):

        order = self.create_order()

        payment_key = uuid.uuid4()

        self.authenticate()

        with patch("payments.services.initialize_transaction") as mocked_initialize:

            mocked_initialize.side_effect = self.paystack_initialization_response

            first_response = self.client.post(
                self.payment_initialize_url(order),
                {
                    "idempotency_key": str(payment_key),
                },
                format="json",
            )

            second_response = self.client.post(
                self.payment_initialize_url(order),
                {
                    "idempotency_key": str(payment_key),
                },
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

        self.assertEqual(
            first_response.data["id"],
            second_response.data["id"],
        )

        self.assertEqual(
            first_response.data["reference"],
            second_response.data["reference"],
        )

        self.assertEqual(
            Payment.objects.filter(
                order=order,
            ).count(),
            1,
        )

        mocked_initialize.assert_called_once()

    def test_successful_verification_commits_inventory_once(
        self,
    ):

        order = self.create_order()

        payment, _response, _key = self.initialize_payment(order)

        verification_response = self.paystack_verification_response(
            payment,
        )

        self.authenticate()

        with patch("payments.services.verify_transaction") as mocked_verify:

            mocked_verify.return_value = verification_response

            first_response = self.client.post(
                self.payment_verify_url(payment),
                {},
                format="json",
            )

            second_response = self.client.post(
                self.payment_verify_url(payment),
                {},
                format="json",
            )

        self.assertEqual(
            first_response.status_code,
            status.HTTP_200_OK,
        )

        self.assertEqual(
            second_response.status_code,
            status.HTTP_200_OK,
        )

        self.assertEqual(
            first_response.data["status"],
            Payment.Status.SUCCESSFUL,
        )

        self.assertTrue(
            first_response.data["finalized"],
        )

        self.assertFalse(
            second_response.data["finalized"],
        )

        payment.refresh_from_db()

        order.refresh_from_db()

        self.inventory.refresh_from_db()

        self.assertEqual(
            payment.status,
            Payment.Status.SUCCESSFUL,
        )

        self.assertEqual(
            payment.provider_status,
            "success",
        )

        self.assertEqual(
            order.status,
            Order.Status.CONFIRMED,
        )

        self.assertEqual(
            order.inventory_status,
            Order.InventoryStatus.COMMITTED,
        )

        self.assertEqual(
            self.inventory.quantity,
            9,
        )

        self.assertEqual(
            self.inventory.reserved_quantity,
            0,
        )

        mocked_verify.assert_called_once_with(
            reference=payment.reference,
        )

    def test_amount_mismatch_does_not_commit_order(
        self,
    ):

        order = self.create_order()

        payment, _response, _key = self.initialize_payment(order)

        verification_response = self.paystack_verification_response(
            payment,
            amount=payment.amount_subunit - 100,
        )

        self.authenticate()

        with patch(
            "payments.services.verify_transaction",
            return_value=verification_response,
        ):

            response = self.client.post(
                self.payment_verify_url(payment),
                {},
                format="json",
            )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

        self.assertIn(
            "amount",
            response.data["detail"].lower(),
        )

        payment.refresh_from_db()

        order.refresh_from_db()

        self.inventory.refresh_from_db()

        self.assertEqual(
            payment.status,
            Payment.Status.PENDING,
        )

        self.assertEqual(
            order.status,
            Order.Status.PENDING_PAYMENT,
        )

        self.assertEqual(
            order.inventory_status,
            Order.InventoryStatus.RESERVED,
        )

        self.assertEqual(
            self.inventory.quantity,
            10,
        )

        self.assertEqual(
            self.inventory.reserved_quantity,
            1,
        )

    def test_failed_payment_does_not_commit_inventory(
        self,
    ):

        order = self.create_order()

        payment, _response, _key = self.initialize_payment(order)

        verification_response = self.paystack_verification_response(
            payment,
            provider_status="failed",
        )

        self.authenticate()

        with patch(
            "payments.services.verify_transaction",
            return_value=verification_response,
        ):

            response = self.client.post(
                self.payment_verify_url(payment),
                {},
                format="json",
            )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.assertEqual(
            response.data["status"],
            Payment.Status.FAILED,
        )

        self.assertFalse(
            response.data["finalized"],
        )

        payment.refresh_from_db()

        order.refresh_from_db()

        self.inventory.refresh_from_db()

        self.assertEqual(
            payment.status,
            Payment.Status.FAILED,
        )

        self.assertEqual(
            order.status,
            Order.Status.PENDING_PAYMENT,
        )

        self.assertEqual(
            order.inventory_status,
            Order.InventoryStatus.RESERVED,
        )

        self.assertEqual(
            self.inventory.quantity,
            10,
        )

        self.assertEqual(
            self.inventory.reserved_quantity,
            1,
        )

    def test_webhook_rejects_invalid_signature(
        self,
    ):

        response, _raw_body = self.post_webhook(
            {
                "event": "charge.success",
                "data": {
                    "reference": "PAY-INVALID",
                },
            },
            signature="invalid-signature",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_401_UNAUTHORIZED,
        )

        self.assertEqual(
            WebhookEvent.objects.count(),
            0,
        )

    def test_valid_webhook_finalizes_payment_once(
        self,
    ):

        order = self.create_order()

        payment, _response, _key = self.initialize_payment(order)

        payload = {
            "event": "charge.success",
            "data": {
                "reference": payment.reference,
            },
        }

        verification_response = self.paystack_verification_response(
            payment,
        )

        self.client.force_authenticate(user=None)

        with patch("payments.services.verify_transaction") as mocked_verify:

            mocked_verify.return_value = verification_response

            first_response, raw_body = self.post_webhook(payload)

            second_response = self.client.generic(
                "POST",
                self.webhook_url,
                raw_body,
                content_type="application/json",
                HTTP_X_PAYSTACK_SIGNATURE=(self.webhook_signature(raw_body)),
            )

        self.assertEqual(
            first_response.status_code,
            status.HTTP_200_OK,
        )

        self.assertEqual(
            second_response.status_code,
            status.HTTP_200_OK,
        )

        self.assertTrue(
            first_response.data["processed"],
        )

        self.assertTrue(
            first_response.data["finalized"],
        )

        self.assertFalse(
            second_response.data["finalized"],
        )

        payment.refresh_from_db()

        order.refresh_from_db()

        self.inventory.refresh_from_db()

        self.assertEqual(
            payment.status,
            Payment.Status.SUCCESSFUL,
        )

        self.assertEqual(
            order.status,
            Order.Status.CONFIRMED,
        )

        self.assertEqual(
            order.inventory_status,
            Order.InventoryStatus.COMMITTED,
        )

        self.assertEqual(
            self.inventory.quantity,
            9,
        )

        self.assertEqual(
            self.inventory.reserved_quantity,
            0,
        )

        self.assertEqual(
            WebhookEvent.objects.count(),
            1,
        )

        event = WebhookEvent.objects.get()

        self.assertEqual(
            event.event_type,
            "charge.success",
        )

        self.assertEqual(
            event.reference,
            payment.reference,
        )

        self.assertTrue(event.processed)

        self.assertEqual(
            event.payload_hash,
            hashlib.sha256(raw_body).hexdigest(),
        )

        mocked_verify.assert_called_once_with(
            reference=payment.reference,
        )

    def test_expiration_reconciles_successful_payment(
        self,
    ):

        order = self.create_order()

        payment, _response, _key = self.initialize_payment(order)

        paid_at = timezone.now() - timedelta(
            minutes=2,
        )

        order.reservation_expires_at = timezone.now() - timedelta(minutes=1)

        order.save(
            update_fields=[
                "reservation_expires_at",
                "updated_at",
            ]
        )

        verification_response = self.paystack_verification_response(
            payment,
            paid_at=paid_at,
        )

        command_output = StringIO()

        with patch(
            "payments.services.verify_transaction",
            return_value=verification_response,
        ):

            call_command(
                "release_expired_orders",
                stdout=command_output,
            )

        payment.refresh_from_db()

        order.refresh_from_db()

        self.inventory.refresh_from_db()

        self.assertEqual(
            payment.status,
            Payment.Status.SUCCESSFUL,
        )

        self.assertEqual(
            order.status,
            Order.Status.CONFIRMED,
        )

        self.assertEqual(
            order.inventory_status,
            Order.InventoryStatus.COMMITTED,
        )

        self.assertEqual(
            self.inventory.quantity,
            9,
        )

        self.assertEqual(
            self.inventory.reserved_quantity,
            0,
        )

        self.assertIn(
            "Expired 0 order(s)",
            command_output.getvalue(),
        )

        self.assertIn(
            "skipped 1",
            command_output.getvalue(),
        )

    def test_refund_initialization_requires_authentication(self):

        _order, payment = self.create_successful_payment()

        self.client.force_authenticate(user=None)

        response = self.client.post(
            self.staff_refund_url(payment),
            {
                "reason": "Customer cancellation approved.",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_401_UNAUTHORIZED,
        )

        self.assertEqual(
            Refund.objects.count(),
            0,
        )

    def test_customer_cannot_initiate_refund(self):

        _order, payment = self.create_successful_payment()

        self.authenticate(self.user)

        response = self.client.post(
            self.staff_refund_url(payment),
            {
                "reason": "Customer attempting to initiate a refund.",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_403_FORBIDDEN,
        )

        self.assertEqual(
            Refund.objects.count(),
            0,
        )

    def test_staff_can_initiate_full_refund(self):

        order, payment = self.create_successful_payment()

        refund, response, mocked_refund = self.initialize_refund(
            payment,
        )

        self.assertTrue(
            response.data["initiated"],
        )

        self.assertEqual(
            refund.status,
            Refund.Status.PENDING,
        )

        self.assertEqual(
            refund.provider_status,
            "pending",
        )

        self.assertEqual(
            refund.amount,
            payment.amount,
        )

        self.assertEqual(
            refund.amount_subunit,
            payment.amount_subunit,
        )

        self.assertEqual(
            refund.requested_by,
            self.staff_user,
        )

        self.assertEqual(
            refund.requested_by_email,
            self.staff_user.email,
        )

        payment.refresh_from_db()

        order.refresh_from_db()

        self.assertEqual(
            payment.status,
            Payment.Status.SUCCESSFUL,
        )

        self.assertEqual(
            payment.provider_status,
            "reversal pending",
        )

        self.assertEqual(
            order.status,
            Order.Status.CONFIRMED,
        )

        mocked_refund.assert_called_once()

    def test_refund_initialization_is_idempotent(self):

        _order, payment = self.create_successful_payment()

        self.authenticate(self.staff_user)

        provider_response = self.paystack_refund_response(
            payment,
        )

        request_data = {
            "reason": "Customer cancellation approved before dispatch.",
        }

        with patch(
            "payments.services.create_paystack_refund",
            return_value=provider_response,
        ) as mocked_refund:

            first_response = self.client.post(
                self.staff_refund_url(payment),
                request_data,
                format="json",
            )

            second_response = self.client.post(
                self.staff_refund_url(payment),
                request_data,
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

        self.assertTrue(
            first_response.data["initiated"],
        )

        self.assertFalse(
            second_response.data["initiated"],
        )

        self.assertEqual(
            first_response.data["reference"],
            second_response.data["reference"],
        )

        self.assertEqual(
            Refund.objects.count(),
            1,
        )

        mocked_refund.assert_called_once()

    def test_paystack_refund_failure_is_recorded(self):

        _order, payment = self.create_successful_payment()

        self.authenticate(self.staff_user)

        provider_error = PaystackAPIError(
            "Paystack rejected the refund.",
            status_code=400,
            response_data={
                "status": False,
                "message": "Paystack rejected the refund.",
            },
        )

        with patch(
            "payments.services.create_paystack_refund",
            side_effect=provider_error,
        ):

            response = self.client.post(
                self.staff_refund_url(payment),
                {
                    "reason": "Customer cancellation approved.",
                },
                format="json",
            )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

        refund = Refund.objects.get(
            payment=payment,
        )

        self.assertEqual(
            refund.status,
            Refund.Status.FAILED,
        )

        self.assertEqual(
            refund.failure_message,
            "Paystack rejected the refund.",
        )

        payment.refresh_from_db()

        self.assertEqual(
            payment.status,
            Payment.Status.SUCCESSFUL,
        )

    def test_customer_can_list_and_retrieve_own_refund(self):

        _order, payment = self.create_successful_payment()

        refund, _response, _mock = self.initialize_refund(
            payment,
        )

        self.authenticate(self.user)

        list_response = self.client.get(
            self.customer_refund_list_url(),
        )

        detail_response = self.client.get(
            self.customer_refund_detail_url(refund),
        )

        self.assertEqual(
            list_response.status_code,
            status.HTTP_200_OK,
        )

        self.assertEqual(
            list_response.data["count"],
            1,
        )

        self.assertEqual(
            list_response.data["results"][0]["reference"],
            refund.reference,
        )

        self.assertEqual(
            detail_response.status_code,
            status.HTTP_200_OK,
        )

        self.assertEqual(
            detail_response.data["reference"],
            refund.reference,
        )

        self.assertNotIn(
            "requested_by_email",
            detail_response.data,
        )

        self.assertNotIn(
            "initialization_response",
            detail_response.data,
        )

    def test_customer_cannot_retrieve_another_users_refund(self):

        _order, payment = self.create_successful_payment()

        refund, _response, _mock = self.initialize_refund(
            payment,
        )

        self.authenticate(self.other_user)

        response = self.client.get(
            self.customer_refund_detail_url(refund),
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_404_NOT_FOUND,
        )

    def test_refund_progress_webhooks_update_status(self):

        _order, payment = self.create_successful_payment()

        refund, _response, _mock = self.initialize_refund(
            payment,
        )

        self.client.force_authenticate(user=None)

        progress_events = [
            ("refund.processing", Refund.Status.PROCESSING),
            (
                "refund.needs-attention",
                Refund.Status.NEEDS_ATTENTION,
            ),
        ]

        for event_type, expected_status in progress_events:

            with self.subTest(event_type=event_type):

                response, _raw_body = self.post_webhook(
                    self.refund_webhook_payload(
                        refund,
                        event_type,
                    )
                )

                self.assertEqual(
                    response.status_code,
                    status.HTTP_200_OK,
                )

                self.assertTrue(
                    response.data["processed"],
                )

                self.assertTrue(
                    response.data["finalized"],
                )

                refund.refresh_from_db()

                payment.refresh_from_db()

                self.assertEqual(
                    refund.status,
                    expected_status,
                )

                self.assertEqual(
                    payment.status,
                    Payment.Status.SUCCESSFUL,
                )

                self.assertEqual(
                    payment.provider_status,
                    "reversal pending",
                )

    def test_refund_processed_webhook_marks_payment_refunded(self):

        order, payment = self.create_successful_payment()

        refund, _response, _mock = self.initialize_refund(
            payment,
        )

        self.client.force_authenticate(user=None)

        response, _raw_body = self.post_webhook(
            self.refund_webhook_payload(
                refund,
                "refund.processed",
            )
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.assertTrue(
            response.data["finalized"],
        )

        refund.refresh_from_db()

        payment.refresh_from_db()

        order.refresh_from_db()

        self.assertEqual(
            refund.status,
            Refund.Status.PROCESSED,
        )

        self.assertIsNotNone(
            refund.processed_at,
        )

        self.assertEqual(
            payment.status,
            Payment.Status.REFUNDED,
        )

        self.assertEqual(
            payment.provider_status,
            "reversed",
        )

        self.assertEqual(
            order.status,
            Order.Status.CONFIRMED,
        )

    def test_refund_failed_webhook_keeps_payment_successful(self):

        _order, payment = self.create_successful_payment()

        refund, _response, _mock = self.initialize_refund(
            payment,
        )

        self.client.force_authenticate(user=None)

        response, _raw_body = self.post_webhook(
            self.refund_webhook_payload(
                refund,
                "refund.failed",
                reason="Refund rejected by the provider.",
            )
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        refund.refresh_from_db()

        payment.refresh_from_db()

        self.assertEqual(
            refund.status,
            Refund.Status.FAILED,
        )

        self.assertEqual(
            refund.failure_message,
            "Refund rejected by the provider.",
        )

        self.assertEqual(
            payment.status,
            Payment.Status.SUCCESSFUL,
        )

        self.assertEqual(
            payment.provider_status,
            "success",
        )

    def test_duplicate_refund_webhook_is_idempotent(self):

        _order, payment = self.create_successful_payment()

        refund, _response, _mock = self.initialize_refund(
            payment,
        )

        payload = self.refund_webhook_payload(
            refund,
            "refund.processed",
        )

        self.client.force_authenticate(user=None)

        first_response, raw_body = self.post_webhook(payload)

        second_response = self.client.generic(
            "POST",
            self.webhook_url,
            raw_body,
            content_type="application/json",
            HTTP_X_PAYSTACK_SIGNATURE=(self.webhook_signature(raw_body)),
        )

        self.assertEqual(
            first_response.status_code,
            status.HTTP_200_OK,
        )

        self.assertEqual(
            second_response.status_code,
            status.HTTP_200_OK,
        )

        self.assertTrue(
            first_response.data["finalized"],
        )

        self.assertFalse(
            second_response.data["finalized"],
        )

        self.assertEqual(
            WebhookEvent.objects.filter(
                event_type="refund.processed",
            ).count(),
            1,
        )

        refund.refresh_from_db()

        payment.refresh_from_db()

        self.assertEqual(
            refund.status,
            Refund.Status.PROCESSED,
        )

        self.assertEqual(
            payment.status,
            Payment.Status.REFUNDED,
        )

    def test_invalid_refund_webhook_amount_is_recorded(self):

        _order, payment = self.create_successful_payment()

        refund, _response, _mock = self.initialize_refund(
            payment,
        )

        payload = self.refund_webhook_payload(
            refund,
            "refund.processed",
        )

        payload["data"]["amount"] += 100

        self.client.force_authenticate(user=None)

        response, _raw_body = self.post_webhook(payload)

        self.assertEqual(
            response.status_code,
            status.HTTP_503_SERVICE_UNAVAILABLE,
        )

        refund.refresh_from_db()

        payment.refresh_from_db()

        self.assertEqual(
            refund.status,
            Refund.Status.PENDING,
        )

        self.assertEqual(
            payment.status,
            Payment.Status.SUCCESSFUL,
        )

        event = WebhookEvent.objects.get(
            event_type="refund.processed",
        )

        self.assertFalse(
            event.processed,
        )

        self.assertIn(
            "amount does not match",
            event.processing_error.lower(),
        )