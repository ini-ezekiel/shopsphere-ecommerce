from decimal import Decimal


from django.contrib.auth import get_user_model

from django.urls import reverse

from django.utils import timezone

from rest_framework import status

from rest_framework.test import APITestCase


from addresses.models import (
    DeliveryLocation,
    ShippingAddress,
)

from orders.models import (
    Order,
    OrderItem,
    OrderStatusHistory,
)

from orders.serializers import OrderSerializer

from payments.models import Payment, Refund

from products.models import (
    Brand,
    Category,
    Inventory,
    Product,
    ProductVariant,
)


from .models import Shipment

from .serializers import FulfillmentOrderSerializer

User = get_user_model()


class FulfillmentAPITests(APITestCase):

    def setUp(self):

        self.customer = User.objects.create_user(
            username="shipping_customer",
            email="shipping-customer@example.com",
            password="StrongPassword123!",
            is_email_verified=True,
        )

        self.staff_user = User.objects.create_user(
            username="shipping_staff",
            email="shipping-staff@example.com",
            password="StrongPassword123!",
            is_email_verified=True,
            is_staff=True,
            is_active=True,
        )

        self.inactive_staff = User.objects.create_user(
            username="inactive_shipping_staff",
            email="inactive-shipping-staff@example.com",
            password="StrongPassword123!",
            is_email_verified=True,
            is_staff=True,
            is_active=False,
        )

        self.brand = Brand.objects.create(
            name="Shipping Puma",
            slug="shipping-puma",
            is_active=True,
        )

        self.category = Category.objects.create(
            name="Shipping Sneakers",
            slug="shipping-sneakers",
            description="Sneakers used for shipping tests.",
            is_active=True,
        )

        self.product = Product.objects.create(
            category=self.category,
            brand=self.brand,
            name="Shipping Test Sneaker",
            slug="shipping-test-sneaker",
            description="A product used for shipping tests.",
            is_active=True,
        )

        self.variant = ProductVariant.objects.create(
            product=self.product,
            name="White / Size 42",
            sku="SHIPPING-PUMA-WHT-42",
            attributes={
                "size": "42",
                "color": "White",
            },
            price=Decimal("40000.00"),
            is_active=True,
        )

        self.inventory = Inventory.objects.create(
            variant=self.variant,
            quantity=9,
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
            user=self.customer,
            delivery_location=self.location,
            label="home",
            recipient_name="Shipping Customer",
            phone_number="08012345678",
            address_line_1="12 Shipping Street",
            address_line_2="",
            landmark="Near Shipping Junction",
            postal_code="520101",
            is_default=True,
        )

        self.order = self.create_order()

        self.list_url = reverse(
            "shipping:staff-order-list",
        )

    def authenticate(self, user=None):

        self.client.force_authenticate(
            user=user or self.staff_user,
        )

    def create_order(
        self,
        *,
        status_value=Order.Status.CONFIRMED,
        inventory_status=Order.InventoryStatus.COMMITTED,
        include_successful_payment=True,
    ):

        order = Order.objects.create(
            user=self.customer,
            status=status_value,
            inventory_status=inventory_status,
            shipping_address=self.address,
            recipient_name=self.address.recipient_name,
            phone_number=self.address.phone_number,
            address_line_1=self.address.address_line_1,
            address_line_2=self.address.address_line_2,
            landmark=self.address.landmark,
            postal_code=self.address.postal_code,
            city=self.location.city,
            state=self.location.state,
            country="Nigeria",
            estimated_delivery_days=(self.location.estimated_delivery_days),
            subtotal=Decimal("40000.00"),
            discount_amount=Decimal("0.00"),
            shipping_fee=Decimal("2500.00"),
            total_amount=Decimal("42500.00"),
            reservation_expires_at=timezone.now(),
        )

        OrderItem.objects.create(
            order=order,
            variant=self.variant,
            product_name=self.product.name,
            variant_name=self.variant.name,
            sku=self.variant.sku,
            attributes=dict(self.variant.attributes),
            unit_price=Decimal("40000.00"),
            quantity=1,
            line_total=Decimal("40000.00"),
        )

        if include_successful_payment:

            Payment.objects.create(
                order=order,
                status=Payment.Status.SUCCESSFUL,
                provider_status="success",
                amount=Decimal("42500.00"),
                amount_subunit=4250000,
                currency="NGN",
                channel="card",
                gateway_response="Successful",
                paid_at=timezone.now(),
                verified_at=timezone.now(),
            )

        return order

    def detail_url(self, order=None):

        order = order or self.order

        return reverse(
            "shipping:staff-order-detail",
            args=[order.order_number],
        )

    def transition_url(self, order=None):

        order = order or self.order

        return reverse(
            "shipping:staff-order-status-update",
            args=[order.order_number],
        )

    def transition(
        self,
        order,
        new_status,
        *,
        note="",
        carrier="",
        tracking_number="",
    ):

        request_data = {
            "status": new_status,
            "note": note,
        }

        if carrier:

            request_data["carrier"] = carrier

        if tracking_number:

            request_data["tracking_number"] = tracking_number

        return self.client.patch(
            self.transition_url(order),
            request_data,
            format="json",
        )

    def move_to_processing(self, order=None):

        order = order or self.order

        response = self.transition(
            order,
            Order.Status.PROCESSING,
            note="Order accepted for fulfilment.",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        return response

    def move_to_shipped(
        self,
        order=None,
        *,
        tracking_number="DHL-TEST-001",
    ):

        order = order or self.order

        response = self.transition(
            order,
            Order.Status.SHIPPED,
            note="Package dispatched.",
            carrier="DHL",
            tracking_number=tracking_number,
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        return response

    def test_staff_endpoints_require_authentication(self):

        self.client.force_authenticate(user=None)

        list_response = self.client.get(
            self.list_url,
        )

        detail_response = self.client.get(
            self.detail_url(),
        )

        transition_response = self.client.patch(
            self.transition_url(),
            {
                "status": Order.Status.PROCESSING,
            },
            format="json",
        )

        self.assertEqual(
            list_response.status_code,
            status.HTTP_401_UNAUTHORIZED,
        )

        self.assertEqual(
            detail_response.status_code,
            status.HTTP_401_UNAUTHORIZED,
        )

        self.assertEqual(
            transition_response.status_code,
            status.HTTP_401_UNAUTHORIZED,
        )

    def test_customer_cannot_access_staff_endpoints(self):

        self.authenticate(self.customer)

        list_response = self.client.get(
            self.list_url,
        )

        detail_response = self.client.get(
            self.detail_url(),
        )

        transition_response = self.client.patch(
            self.transition_url(),
            {
                "status": Order.Status.PROCESSING,
            },
            format="json",
        )

        self.assertEqual(
            list_response.status_code,
            status.HTTP_403_FORBIDDEN,
        )

        self.assertEqual(
            detail_response.status_code,
            status.HTTP_403_FORBIDDEN,
        )

        self.assertEqual(
            transition_response.status_code,
            status.HTTP_403_FORBIDDEN,
        )

    def test_inactive_staff_cannot_manage_fulfillment(self):

        self.authenticate(self.inactive_staff)

        response = self.client.get(
            self.list_url,
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_403_FORBIDDEN,
        )

    def test_staff_can_list_filter_and_retrieve_orders(self):

        cancelled_order = self.create_order(
            status_value=Order.Status.CANCELLED,
            inventory_status=Order.InventoryStatus.RELEASED,
            include_successful_payment=False,
        )

        self.authenticate()

        list_response = self.client.get(
            self.list_url,
            {
                "status": Order.Status.CONFIRMED,
            },
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
            list_response.data["results"][0]["order_number"],
            self.order.order_number,
        )

        detail_response = self.client.get(
            self.detail_url(),
        )

        self.assertEqual(
            detail_response.status_code,
            status.HTTP_200_OK,
        )

        self.assertEqual(
            detail_response.data["customer_email"],
            self.customer.email,
        )

        self.assertEqual(
            detail_response.data["items"][0]["sku"],
            self.variant.sku,
        )

        self.assertEqual(
            detail_response.data["delivery_address"]["city"],
            self.location.city,
        )

        self.assertNotEqual(
            cancelled_order.status,
            self.order.status,
        )

    def test_invalid_status_filter_is_rejected(self):

        self.authenticate()

        response = self.client.get(
            self.list_url,
            {
                "status": "unknown",
            },
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

        self.assertIn(
            "status",
            response.data,
        )

    def test_missing_staff_order_detail_returns_not_found(self):

        self.authenticate()

        url = reverse(
            "shipping:staff-order-detail",
            args=["ORD-DOES-NOT-EXIST"],
        )

        response = self.client.get(
            url,
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_404_NOT_FOUND,
        )

    def test_confirmed_paid_order_can_enter_processing(self):

        self.authenticate()

        response = self.move_to_processing()

        self.assertTrue(
            response.data["transitioned"],
        )

        self.order.refresh_from_db()

        self.assertEqual(
            self.order.status,
            Order.Status.PROCESSING,
        )

        shipment = Shipment.objects.get(
            order=self.order,
        )

        self.assertEqual(
            shipment.status,
            Shipment.Status.PREPARING,
        )

        self.assertEqual(
            shipment.created_by,
            self.staff_user,
        )

        history = OrderStatusHistory.objects.get(
            order=self.order,
        )

        self.assertEqual(
            history.from_status,
            Order.Status.CONFIRMED,
        )

        self.assertEqual(
            history.to_status,
            Order.Status.PROCESSING,
        )

        self.assertEqual(
            history.changed_by_email,
            self.staff_user.email,
        )

    def test_processing_transition_is_idempotent(self):

        self.authenticate()

        first_response = self.move_to_processing()

        second_response = self.transition(
            self.order,
            Order.Status.PROCESSING,
            note="Repeated processing request.",
        )

        self.assertTrue(
            first_response.data["transitioned"],
        )

        self.assertEqual(
            second_response.status_code,
            status.HTTP_200_OK,
        )

        self.assertFalse(
            second_response.data["transitioned"],
        )

        self.assertEqual(
            OrderStatusHistory.objects.filter(
                order=self.order,
            ).count(),
            1,
        )

        self.assertEqual(
            Shipment.objects.filter(
                order=self.order,
            ).count(),
            1,
        )

    def test_order_without_successful_payment_cannot_be_processed(self):

        unpaid_order = self.create_order(
            include_successful_payment=False,
        )

        self.authenticate()

        response = self.transition(
            unpaid_order,
            Order.Status.PROCESSING,
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

        unpaid_order.refresh_from_db()

        self.assertEqual(
            unpaid_order.status,
            Order.Status.CONFIRMED,
        )

        self.assertFalse(
            Shipment.objects.filter(
                order=unpaid_order,
            ).exists()
        )

    def test_order_cannot_skip_processing_status(self):

        self.authenticate()

        response = self.transition(
            self.order,
            Order.Status.SHIPPED,
            carrier="DHL",
            tracking_number="DHL-SKIP-001",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

        self.order.refresh_from_db()

        self.assertEqual(
            self.order.status,
            Order.Status.CONFIRMED,
        )

        self.assertEqual(
            OrderStatusHistory.objects.filter(
                order=self.order,
            ).count(),
            0,
        )

    def test_shipping_requires_carrier_and_tracking_number(self):

        self.authenticate()

        self.move_to_processing()

        response = self.client.patch(
            self.transition_url(),
            {
                "status": Order.Status.SHIPPED,
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

        self.assertIn(
            "carrier",
            response.data,
        )

        self.order.refresh_from_db()

        self.assertEqual(
            self.order.status,
            Order.Status.PROCESSING,
        )

    def test_duplicate_tracking_number_is_rejected(self):

        second_order = self.create_order()

        self.authenticate()

        self.move_to_processing(self.order)

        self.move_to_shipped(
            self.order,
            tracking_number="DHL-DUPLICATE-001",
        )

        self.move_to_processing(second_order)

        duplicate_response = self.transition(
            second_order,
            Order.Status.SHIPPED,
            carrier="DHL",
            tracking_number="DHL-DUPLICATE-001",
        )

        self.assertEqual(
            duplicate_response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

        second_order.refresh_from_db()

        self.assertEqual(
            second_order.status,
            Order.Status.PROCESSING,
        )

        second_shipment = Shipment.objects.get(
            order=second_order,
        )

        self.assertEqual(
            second_shipment.status,
            Shipment.Status.PREPARING,
        )

    def test_complete_fulfillment_workflow_and_inventory_consistency(
        self,
    ):

        original_quantity = self.inventory.quantity

        original_reserved = self.inventory.reserved_quantity

        self.authenticate()

        processing_response = self.move_to_processing()

        shipping_response = self.move_to_shipped(
            tracking_number="DHL-COMPLETE-001",
        )

        backward_response = self.transition(
            self.order,
            Order.Status.PROCESSING,
            note="Invalid backward transition.",
        )

        delivered_response = self.transition(
            self.order,
            Order.Status.DELIVERED,
            note="Customer delivery confirmed.",
        )

        repeated_delivery_response = self.transition(
            self.order,
            Order.Status.DELIVERED,
            note="Repeated delivery request.",
        )

        self.assertTrue(
            processing_response.data["transitioned"],
        )

        self.assertTrue(
            shipping_response.data["transitioned"],
        )

        self.assertEqual(
            backward_response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

        self.assertEqual(
            delivered_response.status_code,
            status.HTTP_200_OK,
        )

        self.assertTrue(
            delivered_response.data["transitioned"],
        )

        self.assertEqual(
            repeated_delivery_response.status_code,
            status.HTTP_200_OK,
        )

        self.assertFalse(
            repeated_delivery_response.data["transitioned"],
        )

        self.order.refresh_from_db()

        self.inventory.refresh_from_db()

        shipment = Shipment.objects.get(
            order=self.order,
        )

        self.assertEqual(
            self.order.status,
            Order.Status.DELIVERED,
        )

        self.assertEqual(
            self.order.inventory_status,
            Order.InventoryStatus.COMMITTED,
        )

        self.assertEqual(
            shipment.status,
            Shipment.Status.DELIVERED,
        )

        self.assertIsNotNone(
            shipment.shipped_at,
        )

        self.assertIsNotNone(
            shipment.delivered_at,
        )

        self.assertGreaterEqual(
            shipment.delivered_at,
            shipment.shipped_at,
        )

        self.assertEqual(
            OrderStatusHistory.objects.filter(
                order=self.order,
            ).count(),
            3,
        )

        self.assertEqual(
            self.inventory.quantity,
            original_quantity,
        )

        self.assertEqual(
            self.inventory.reserved_quantity,
            original_reserved,
        )

        self.assertEqual(
            self.inventory.available_quantity,
            original_quantity - original_reserved,
        )

    def test_tracking_number_search_finds_order(self):

        self.authenticate()

        self.move_to_processing()

        self.move_to_shipped(
            tracking_number="DHL-SEARCH-001",
        )

        response = self.client.get(
            self.list_url,
            {
                "search": "DHL-SEARCH-001",
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
            response.data["results"][0]["order_number"],
            self.order.order_number,
        )

    def test_customer_serializer_hides_staff_email(self):

        self.authenticate()

        self.move_to_processing()

        self.order.refresh_from_db()

        customer_data = OrderSerializer(
            self.order,
        ).data

        staff_data = FulfillmentOrderSerializer(
            self.order,
        ).data

        customer_history = customer_data["status_history"][0]

        staff_history = staff_data["status_history"][0]

        self.assertNotIn(
            "changed_by_email",
            customer_history,
        )

        self.assertEqual(
            staff_history["changed_by_email"],
            self.staff_user.email,
        )

    def create_refund(
        self,
        *,
        status_value,
    ):
        payment = self.order.payments.get(
            status=Payment.Status.SUCCESSFUL,
        )

        return Refund.objects.create(
            payment=payment,
            requested_by=self.staff_user,
            requested_by_email=self.staff_user.email,
            status=status_value,
            provider_status=status_value,
            amount=payment.amount,
            amount_subunit=payment.amount_subunit,
            currency=payment.currency,
            reason="Customer cancellation approved before dispatch.",
        )

    def test_active_refund_blocks_order_processing(self):
        self.authenticate()

        blocking_statuses = [
            Refund.Status.INITIALIZED,
            Refund.Status.PENDING,
            Refund.Status.PROCESSING,
            Refund.Status.NEEDS_ATTENTION,
        ]

        for refund_status in blocking_statuses:
            with self.subTest(refund_status=refund_status):
                refund = self.create_refund(
                    status_value=refund_status,
                )

                response = self.transition(
                    self.order,
                    Order.Status.PROCESSING,
                    note="Attempting fulfilment during a refund.",
                )

                self.assertEqual(
                    response.status_code,
                    status.HTTP_400_BAD_REQUEST,
                )

                self.assertIn(
                    "refund",
                    response.data["detail"].lower(),
                )

                self.order.refresh_from_db()

                self.assertEqual(
                    self.order.status,
                    Order.Status.CONFIRMED,
                )

                self.assertFalse(
                    Shipment.objects.filter(
                        order=self.order,
                    ).exists()
                )

                self.assertEqual(
                    self.order.status_history.count(),
                    0,
                )

                refund.delete()

    def test_processed_refund_blocks_order_processing(self):
        self.authenticate()

        self.create_refund(
            status_value=Refund.Status.PROCESSED,
        )

        response = self.transition(
            self.order,
            Order.Status.PROCESSING,
            note="Attempting fulfilment after a completed refund.",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

        self.assertEqual(
            response.data["detail"],
            ("This order has been refunded and cannot continue " "through fulfilment."),
        )

        self.order.refresh_from_db()

        self.assertEqual(
            self.order.status,
            Order.Status.CONFIRMED,
        )

        self.assertFalse(
            Shipment.objects.filter(
                order=self.order,
            ).exists()
        )

    def test_failed_refund_does_not_block_order_processing(self):
        self.authenticate()

        self.create_refund(
            status_value=Refund.Status.FAILED,
        )

        response = self.transition(
            self.order,
            Order.Status.PROCESSING,
            note="Refund failed, so fulfilment may continue.",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.assertTrue(
            response.data["transitioned"],
        )

        self.order.refresh_from_db()

        self.assertEqual(
            self.order.status,
            Order.Status.PROCESSING,
        )

        self.assertEqual(
            self.order.shipment.status,
            Shipment.Status.PREPARING,
        )
