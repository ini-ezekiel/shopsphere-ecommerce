import uuid
from datetime import timedelta
from decimal import Decimal
from io import StringIO

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.management import call_command
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from addresses.models import (
    DeliveryLocation,
    ShippingAddress,
)
from carts.models import Cart, CartItem
from products.models import (
    Brand,
    Category,
    Inventory,
    Product,
    ProductVariant,
)

from .models import Order

User = get_user_model()


class OrderAPITests(APITestCase):
    def setUp(self):
        cache.clear()

        self.user = User.objects.create_user(
            username="order_user",
            email="order@example.com",
            password="StrongPassword123!",
            is_email_verified=True,
        )

        self.other_user = User.objects.create_user(
            username="other_order_user",
            email="otherorder@example.com",
            password="StrongPassword123!",
            is_email_verified=True,
        )

        self.unverified_user = User.objects.create_user(
            username="unverified_order_user",
            email="unverifiedorder@example.com",
            password="StrongPassword123!",
            is_email_verified=False,
        )

        self.brand = Brand.objects.create(
            name="Puma",
            slug="puma",
            is_active=True,
        )

        self.category = Category.objects.create(
            name="Sneakers",
            slug="sneakers",
            description="Sneakers",
            is_active=True,
        )

        self.product = Product.objects.create(
            category=self.category,
            brand=self.brand,
            name="Puma Sneaker",
            slug="puma-sneaker",
            description="A white Puma sneaker.",
            is_active=True,
        )

        self.variant = ProductVariant.objects.create(
            product=self.product,
            name="White / Size 42",
            sku="PUMA-AM-WHT-42",
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
            recipient_name="Test Customer",
            phone_number="08012345678",
            address_line_1="12 Example Street",
            address_line_2="",
            landmark="Near Example Junction",
            postal_code="520101",
            is_default=True,
        )

        self.other_address = ShippingAddress.objects.create(
            user=self.other_user,
            delivery_location=self.location,
            label="home",
            recipient_name="Other Customer",
            phone_number="08098765432",
            address_line_1="10 Other Street",
            address_line_2="",
            landmark="",
            postal_code="",
            is_default=True,
        )

        self.checkout_url = reverse("orders:checkout")
        self.order_list_url = reverse("orders:order-list")

    def tearDown(self):
        cache.clear()

    def authenticate(self, user=None):
        self.client.force_authenticate(user=user or self.user)

    def add_cart_item(self, user=None, quantity=1):
        user = user or self.user

        cart, _created = Cart.objects.get_or_create(user=user)

        return CartItem.objects.create(
            cart=cart,
            variant=self.variant,
            quantity=quantity,
        )

    def checkout_payload(
        self,
        address=None,
        idempotency_key=None,
    ):
        return {
            "idempotency_key": str(idempotency_key or uuid.uuid4()),
            "shipping_address_id": (address or self.address).id,
        }

    def checkout(
        self,
        *,
        user=None,
        address=None,
        idempotency_key=None,
    ):
        user = user or self.user
        address = address or self.address

        self.authenticate(user)

        return self.client.post(
            self.checkout_url,
            self.checkout_payload(
                address=address,
                idempotency_key=idempotency_key,
            ),
            format="json",
        )

    def test_checkout_requires_authentication(self):
        response = self.client.post(
            self.checkout_url,
            self.checkout_payload(),
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_401_UNAUTHORIZED,
        )

    def test_unverified_user_cannot_checkout(self):
        self.add_cart_item(user=self.unverified_user)
        self.authenticate(self.unverified_user)

        response = self.client.post(
            self.checkout_url,
            {
                "idempotency_key": str(uuid.uuid4()),
                "shipping_address_id": self.address.id,
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_403_FORBIDDEN,
        )

    def test_empty_cart_is_rejected(self):
        self.authenticate()

        response = self.client.post(
            self.checkout_url,
            self.checkout_payload(),
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )
        self.assertEqual(
            response.data["detail"],
            "Your cart is empty.",
        )

    def test_user_cannot_use_another_users_address(self):
        self.add_cart_item()
        self.authenticate()

        response = self.client.post(
            self.checkout_url,
            self.checkout_payload(
                address=self.other_address,
            ),
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )
        self.assertIn(
            "shipping_address_id",
            response.data,
        )

    def test_successful_checkout_creates_snapshots(self):
        self.add_cart_item()

        response = self.checkout()

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
        )
        self.assertEqual(
            response.data["status"],
            Order.Status.PENDING_PAYMENT,
        )
        self.assertEqual(
            response.data["inventory_status"],
            Order.InventoryStatus.RESERVED,
        )
        self.assertEqual(
            response.data["subtotal"],
            "40000.00",
        )
        self.assertEqual(
            response.data["shipping_fee"],
            "2500.00",
        )
        self.assertEqual(
            response.data["total_amount"],
            "42500.00",
        )
        self.assertEqual(
            len(response.data["items"]),
            1,
        )
        self.assertEqual(
            response.data["items"][0]["sku"],
            self.variant.sku,
        )
        self.assertEqual(
            response.data["delivery_address"]["city"],
            "Uyo",
        )

        order = Order.objects.get(pk=response.data["id"])

        self.assertIsNotNone(order.reservation_expires_at)
        self.assertEqual(
            order.recipient_name,
            self.address.recipient_name,
        )

        self.inventory.refresh_from_db()

        self.assertEqual(
            self.inventory.quantity,
            10,
        )
        self.assertEqual(
            self.inventory.reserved_quantity,
            1,
        )
        self.assertFalse(CartItem.objects.filter(cart__user=self.user).exists())

    def test_checkout_is_idempotent(self):
        self.add_cart_item()
        checkout_key = uuid.uuid4()

        first_response = self.checkout(
            idempotency_key=checkout_key,
        )
        second_response = self.checkout(
            idempotency_key=checkout_key,
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
            first_response.data["order_number"],
            second_response.data["order_number"],
        )
        self.assertEqual(
            Order.objects.filter(user=self.user).count(),
            1,
        )

        self.inventory.refresh_from_db()

        self.assertEqual(
            self.inventory.reserved_quantity,
            1,
        )

    def test_insufficient_inventory_rolls_back(self):
        self.inventory.quantity = 1
        self.inventory.save(
            update_fields=[
                "quantity",
                "updated_at",
            ]
        )

        self.add_cart_item(quantity=2)

        response = self.checkout()

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )
        self.assertEqual(
            Order.objects.count(),
            0,
        )

        self.inventory.refresh_from_db()

        self.assertEqual(
            self.inventory.reserved_quantity,
            0,
        )
        self.assertTrue(CartItem.objects.filter(cart__user=self.user).exists())

    def test_order_history_is_private(self):
        self.add_cart_item()
        own_response = self.checkout()

        self.add_cart_item(user=self.other_user)
        other_response = self.checkout(
            user=self.other_user,
            address=self.other_address,
        )

        self.authenticate(self.user)

        list_response = self.client.get(self.order_list_url)

        self.assertEqual(
            list_response.status_code,
            status.HTTP_200_OK,
        )
        self.assertEqual(
            list_response.data["count"],
            1,
        )
        self.assertEqual(
            list_response.data["results"][0]["id"],
            own_response.data["id"],
        )

        other_detail_url = reverse(
            "orders:order-detail",
            args=[other_response.data["order_number"]],
        )

        other_detail_response = self.client.get(other_detail_url)

        self.assertEqual(
            other_detail_response.status_code,
            status.HTTP_404_NOT_FOUND,
        )

    def test_customer_cancellation_releases_inventory_once(self):
        self.add_cart_item()
        checkout_response = self.checkout()

        cancel_url = reverse(
            "orders:order-cancel",
            args=[checkout_response.data["order_number"]],
        )

        first_response = self.client.post(
            cancel_url,
            {},
            format="json",
        )
        second_response = self.client.post(
            cancel_url,
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
            Order.Status.CANCELLED,
        )
        self.assertEqual(
            first_response.data["inventory_status"],
            Order.InventoryStatus.RELEASED,
        )
        self.assertEqual(
            first_response.data["cancellation_reason"],
            Order.CancellationReason.CUSTOMER_CANCELLED,
        )

        self.inventory.refresh_from_db()

        self.assertEqual(
            self.inventory.quantity,
            10,
        )
        self.assertEqual(
            self.inventory.reserved_quantity,
            0,
        )

    def test_expiration_command_releases_inventory(self):
        self.add_cart_item()
        checkout_response = self.checkout()

        order = Order.objects.get(pk=checkout_response.data["id"])

        order.reservation_expires_at = timezone.now() - timedelta(minutes=1)
        order.save(
            update_fields=[
                "reservation_expires_at",
                "updated_at",
            ]
        )

        command_output = StringIO()

        call_command(
            "release_expired_orders",
            stdout=command_output,
        )

        order.refresh_from_db()
        self.inventory.refresh_from_db()

        self.assertEqual(
            order.status,
            Order.Status.CANCELLED,
        )
        self.assertEqual(
            order.inventory_status,
            Order.InventoryStatus.RELEASED,
        )
        self.assertEqual(
            order.cancellation_reason,
            Order.CancellationReason.PAYMENT_EXPIRED,
        )
        self.assertEqual(
            self.inventory.reserved_quantity,
            0,
        )
        self.assertIn(
            "Expired 1 order(s)",
            command_output.getvalue(),
        )

    def test_unexpired_order_is_not_released(self):
        self.add_cart_item()
        checkout_response = self.checkout()

        command_output = StringIO()

        call_command(
            "release_expired_orders",
            stdout=command_output,
        )

        order = Order.objects.get(pk=checkout_response.data["id"])
        self.inventory.refresh_from_db()

        self.assertEqual(
            order.status,
            Order.Status.PENDING_PAYMENT,
        )
        self.assertEqual(
            order.inventory_status,
            Order.InventoryStatus.RESERVED,
        )
        self.assertEqual(
            self.inventory.reserved_quantity,
            1,
        )
        self.assertIn(
            "Expired 0 order(s)",
            command_output.getvalue(),
        )
