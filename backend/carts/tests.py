from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from products.models import (
    Brand,
    Category,
    Inventory,
    Product,
    ProductVariant,
)

from .models import Cart, CartItem

User = get_user_model()


class CartAPITests(APITestCase):
    def setUp(self):
        cache.clear()

        self.user = User.objects.create_user(
            username="cart_user",
            email="cart@example.com",
            password="StrongPassword123!",
            is_email_verified=True,
        )

        self.other_user = User.objects.create_user(
            username="other_cart_user",
            email="othercart@example.com",
            password="StrongPassword123!",
            is_email_verified=True,
        )

        self.category = Category.objects.create(
            name="Sneakers",
            slug="sneakers",
        )

        self.brand = Brand.objects.create(
            name="Puma",
            slug="puma",
        )

        self.product = Product.objects.create(
            category=self.category,
            brand=self.brand,
            name="Puma Sneaker",
            slug="puma-sneaker",
            description="A test sneaker.",
            is_active=True,
        )

        self.variant = ProductVariant.objects.create(
            product=self.product,
            name="White / Size 42",
            sku="PUMA-WHT-42-TEST",
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

        self.cart_url = reverse("cart-detail")
        self.add_url = reverse("cart-item-create")
        self.clear_url = reverse("cart-clear")

    def tearDown(self):
        cache.clear()

    def authenticate(self, user=None):
        self.client.force_authenticate(user or self.user)

    def add_item(self, quantity=1):
        return self.client.post(
            self.add_url,
            {
                "variant_id": self.variant.id,
                "quantity": quantity,
            },
            format="json",
        )

    def test_cart_requires_authentication(self):
        response = self.client.get(self.cart_url)

        self.assertEqual(
            response.status_code,
            status.HTTP_401_UNAUTHORIZED,
        )

    def test_new_user_receives_empty_cart(self):
        self.authenticate()

        response = self.client.get(self.cart_url)

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )
        self.assertEqual(response.data["items"], [])
        self.assertEqual(
            response.data["total_quantity"],
            0,
        )
        self.assertEqual(
            response.data["total"],
            "0.00",
        )

    def test_user_can_add_cart_item(self):
        self.authenticate()

        response = self.add_item(quantity=2)

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
        )
        self.assertEqual(response.data["quantity"], 2)
        self.assertEqual(
            response.data["subtotal"],
            "80000.00",
        )

    def test_duplicate_variant_increases_existing_quantity(
        self,
    ):
        self.authenticate()

        first_response = self.add_item(quantity=2)
        second_response = self.add_item(quantity=1)

        self.assertEqual(
            first_response.status_code,
            status.HTTP_201_CREATED,
        )
        self.assertEqual(
            second_response.status_code,
            status.HTTP_200_OK,
        )

        cart = Cart.objects.get(user=self.user)
        item = CartItem.objects.get(
            cart=cart,
            variant=self.variant,
        )

        self.assertEqual(item.quantity, 3)
        self.assertEqual(
            CartItem.objects.filter(cart=cart).count(),
            1,
        )
        self.assertEqual(cart.total_quantity, 3)
        self.assertEqual(
            cart.total,
            Decimal("120000.00"),
        )

    def test_cannot_add_more_than_available_inventory(self):
        self.authenticate()

        response = self.add_item(quantity=11)

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )
        self.assertFalse(
            CartItem.objects.filter(
                cart__user=self.user,
            ).exists()
        )

    def test_user_can_update_cart_item(self):
        self.authenticate()
        add_response = self.add_item(quantity=2)
        item_id = add_response.data["id"]

        response = self.client.patch(
            reverse(
                "cart-item-detail",
                args=[item_id],
            ),
            {"quantity": 1},
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )
        self.assertEqual(response.data["quantity"], 1)

        item = CartItem.objects.get(pk=item_id)
        self.assertEqual(item.quantity, 1)

    def test_empty_update_is_rejected(self):
        self.authenticate()
        add_response = self.add_item()
        item_id = add_response.data["id"]

        response = self.client.patch(
            reverse(
                "cart-item-detail",
                args=[item_id],
            ),
            {},
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

    def test_user_cannot_modify_another_users_item(self):
        other_cart = Cart.objects.create(user=self.other_user)
        other_item = CartItem.objects.create(
            cart=other_cart,
            variant=self.variant,
            quantity=1,
        )

        self.authenticate(self.user)

        response = self.client.patch(
            reverse(
                "cart-item-detail",
                args=[other_item.id],
            ),
            {"quantity": 2},
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_404_NOT_FOUND,
        )

        other_item.refresh_from_db()
        self.assertEqual(other_item.quantity, 1)

    def test_user_can_remove_cart_item(self):
        self.authenticate()
        add_response = self.add_item()
        item_id = add_response.data["id"]

        response = self.client.delete(
            reverse(
                "cart-item-detail",
                args=[item_id],
            )
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_204_NO_CONTENT,
        )
        self.assertFalse(CartItem.objects.filter(pk=item_id).exists())

    def test_user_can_clear_cart(self):
        self.authenticate()
        self.add_item(quantity=2)

        response = self.client.delete(self.clear_url)

        self.assertEqual(
            response.status_code,
            status.HTTP_204_NO_CONTENT,
        )
        self.assertFalse(
            CartItem.objects.filter(
                cart__user=self.user,
            ).exists()
        )

    def test_inactive_variant_cannot_be_added(self):
        self.variant.is_active = False
        self.variant.save(update_fields=["is_active"])
        self.authenticate()

        response = self.add_item()

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )
