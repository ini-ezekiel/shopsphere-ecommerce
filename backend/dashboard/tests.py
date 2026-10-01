from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from orders.models import Order
from payments.models import Payment, Refund
from products.models import (
    Category,
    Inventory,
    Product,
    ProductVariant,
)

User = get_user_model()


class DashboardSummaryAPITests(APITestCase):
    def setUp(self):
        self.staff_user = User.objects.create_user(
            username="dashboard_staff",
            email="dashboard-staff@example.com",
            password="StrongPassword123!",
            is_active=True,
            is_staff=True,
            is_email_verified=True,
        )

        self.customer = User.objects.create_user(
            username="dashboard_customer",
            email="dashboard-customer@example.com",
            password="StrongPassword123!",
            is_active=True,
            is_email_verified=True,
        )

        self.url = reverse(
            "dashboard:staff-dashboard-summary",
        )

    def authenticate(self, user=None):
        self.client.force_authenticate(
            user=user or self.staff_user,
        )

    def create_order(
        self,
        *,
        user=None,
        order_status=Order.Status.PENDING_PAYMENT,
        inventory_status=(Order.InventoryStatus.NOT_RESERVED),
        total_amount=Decimal("1000.00"),
    ):
        user = user or self.customer

        return Order.objects.create(
            user=user,
            status=order_status,
            inventory_status=inventory_status,
            recipient_name="Dashboard Customer",
            phone_number="08012345678",
            address_line_1="12 Dashboard Street",
            address_line_2="",
            landmark="",
            postal_code="520101",
            city="Uyo",
            state="Akwa Ibom",
            country="Nigeria",
            estimated_delivery_days=2,
            currency="NGN",
            subtotal=total_amount,
            discount_amount=Decimal("0.00"),
            shipping_fee=Decimal("0.00"),
            total_amount=total_amount,
        )

    def create_payment(
        self,
        *,
        order,
        payment_status=Payment.Status.SUCCESSFUL,
        amount=None,
        transaction_id=9000000001,
    ):
        amount = amount or order.total_amount

        return Payment.objects.create(
            order=order,
            status=payment_status,
            provider_status=(
                "success"
                if payment_status
                in {
                    Payment.Status.SUCCESSFUL,
                    Payment.Status.REFUNDED,
                }
                else ""
            ),
            amount=amount,
            amount_subunit=int(amount * Decimal("100")),
            currency="NGN",
            provider_transaction_id=transaction_id,
            paid_at=timezone.now(),
            verified_at=timezone.now(),
        )

    def test_dashboard_requires_authentication(self):
        response = self.client.get(self.url)

        self.assertEqual(
            response.status_code,
            status.HTTP_401_UNAUTHORIZED,
        )

    def test_customer_cannot_access_dashboard(self):
        self.authenticate(self.customer)

        response = self.client.get(self.url)

        self.assertEqual(
            response.status_code,
            status.HTTP_403_FORBIDDEN,
        )

        self.assertEqual(
            response.data["detail"],
            ("Only active staff members can access " "the administration dashboard."),
        )

    def test_inactive_staff_cannot_access_dashboard(self):
        inactive_staff = User.objects.create_user(
            username="inactive_dashboard_staff",
            email="inactive-dashboard-staff@example.com",
            password="StrongPassword123!",
            is_active=False,
            is_staff=True,
            is_email_verified=True,
        )

        self.authenticate(inactive_staff)

        response = self.client.get(self.url)

        self.assertEqual(
            response.status_code,
            status.HTTP_403_FORBIDDEN,
        )

    def test_default_period_is_thirty_days(self):
        self.authenticate()

        response = self.client.get(self.url)

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.assertEqual(
            response.data["period"],
            "30d",
        )

        self.assertIsNotNone(
            response.data["period_start"],
        )

    def test_all_period_has_no_start_date(self):
        self.authenticate()

        response = self.client.get(
            self.url,
            {"period": "all"},
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.assertEqual(
            response.data["period"],
            "all",
        )

        self.assertIsNone(
            response.data["period_start"],
        )

    def test_invalid_period_is_rejected(self):
        self.authenticate()

        response = self.client.get(
            self.url,
            {"period": "year"},
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

        self.assertIn(
            "period",
            response.data,
        )

    def test_order_counts_are_grouped_by_status(self):
        statuses = [
            Order.Status.PENDING_PAYMENT,
            Order.Status.CONFIRMED,
            Order.Status.PROCESSING,
            Order.Status.SHIPPED,
            Order.Status.DELIVERED,
            Order.Status.CANCELLED,
        ]

        for order_status in statuses:
            self.create_order(
                order_status=order_status,
            )

        self.authenticate()

        response = self.client.get(
            self.url,
            {"period": "all"},
        )

        order_summary = response.data["orders"]

        self.assertEqual(order_summary["total"], 6)
        self.assertEqual(order_summary["pending_payment"], 1)
        self.assertEqual(order_summary["confirmed"], 1)
        self.assertEqual(order_summary["processing"], 1)
        self.assertEqual(order_summary["shipped"], 1)
        self.assertEqual(order_summary["delivered"], 1)
        self.assertEqual(order_summary["cancelled"], 1)

    def test_financial_summary_subtracts_processed_refunds(self):
        paid_order = self.create_order(
            order_status=Order.Status.CONFIRMED,
            inventory_status=(Order.InventoryStatus.COMMITTED),
            total_amount=Decimal("1000.00"),
        )

        self.create_payment(
            order=paid_order,
            amount=Decimal("1000.00"),
            transaction_id=9000000001,
        )

        refunded_order = self.create_order(
            order_status=Order.Status.CONFIRMED,
            inventory_status=(Order.InventoryStatus.COMMITTED),
            total_amount=Decimal("500.00"),
        )

        refunded_payment = self.create_payment(
            order=refunded_order,
            payment_status=Payment.Status.REFUNDED,
            amount=Decimal("500.00"),
            transaction_id=9000000002,
        )

        Refund.objects.create(
            payment=refunded_payment,
            requested_by=self.staff_user,
            requested_by_email=self.staff_user.email,
            status=Refund.Status.PROCESSED,
            provider_status="processed",
            provider_refund_id="dashboard-refund-1",
            amount=Decimal("500.00"),
            amount_subunit=50000,
            currency="NGN",
            reason="Dashboard financial test.",
            processed_at=timezone.now(),
        )

        self.authenticate()

        response = self.client.get(
            self.url,
            {"period": "all"},
        )

        financial = response.data["financial"]

        self.assertEqual(
            financial["gross_paid_amount"],
            "1500.00",
        )

        self.assertEqual(
            financial["processed_refund_amount"],
            "500.00",
        )

        self.assertEqual(
            financial["net_sales"],
            "1000.00",
        )

    def test_catalog_summary_uses_available_inventory(self):
        category = Category.objects.create(
            name="Dashboard Category",
            slug="dashboard-category",
            is_active=True,
        )

        product = Product.objects.create(
            category=category,
            name="Dashboard Product",
            slug="dashboard-product",
            description="Dashboard product description.",
            is_active=True,
        )

        inventory_values = [
            ("available", 10, 0),
            ("low", 5, 2),
            ("out", 3, 3),
        ]

        for position, (
            label,
            quantity,
            reserved_quantity,
        ) in enumerate(inventory_values, start=1):
            variant = ProductVariant.objects.create(
                product=product,
                name=label.title(),
                sku=f"DASHBOARD-{position}",
                attributes={"stock_state": label},
                price=Decimal("1000.00"),
                is_active=True,
            )

            Inventory.objects.create(
                variant=variant,
                quantity=quantity,
                reserved_quantity=reserved_quantity,
            )

        self.authenticate()

        response = self.client.get(
            self.url,
            {"period": "all"},
        )

        catalog = response.data["catalog"]

        self.assertEqual(catalog["active_products"], 1)
        self.assertEqual(catalog["active_variants"], 3)
        self.assertEqual(catalog["low_stock_variants"], 1)
        self.assertEqual(catalog["out_of_stock_variants"], 1)

    def test_customer_total_excludes_staff_users(self):
        User.objects.create_user(
            username="second_dashboard_customer",
            email="second-dashboard-customer@example.com",
            password="StrongPassword123!",
            is_email_verified=True,
        )

        self.authenticate()

        response = self.client.get(
            self.url,
            {"period": "all"},
        )

        customer_summary = response.data["customers"]

        self.assertEqual(
            customer_summary["total_customers"],
            2,
        )

        self.assertEqual(
            customer_summary["new_customers"],
            2,
        )

    def test_period_filter_excludes_old_orders(self):
        recent_order = self.create_order()
        old_order = self.create_order()

        Order.objects.filter(
            pk=old_order.pk,
        ).update(created_at=(timezone.now() - timedelta(days=60)))

        self.authenticate()

        response = self.client.get(
            self.url,
            {"period": "30d"},
        )

        self.assertEqual(
            response.data["orders"]["total"],
            1,
        )

        self.assertEqual(
            response.data["recent_orders"][0]["order_number"],
            recent_order.order_number,
        )

    def test_recent_orders_are_limited_to_five(self):
        for _index in range(7):
            self.create_order()

        self.authenticate()

        response = self.client.get(
            self.url,
            {"period": "all"},
        )

        self.assertEqual(
            len(response.data["recent_orders"]),
            5,
        )
