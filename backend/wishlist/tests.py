from decimal import Decimal

from django.contrib.auth import get_user_model
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

from .models import WishlistItem

User = get_user_model()


class WishlistAPITests(APITestCase):
    password = "StrongPass123!"

    def setUp(self):
        self.user = User.objects.create_user(
            email="wishlist@example.com",
            username="wishlist_user",
            password=self.password,
            is_email_verified=True,
        )

        self.other_user = User.objects.create_user(
            email="other-wishlist@example.com",
            username="other_wishlist_user",
            password=self.password,
            is_email_verified=True,
        )

        self.brand = Brand.objects.create(
            name="Puma",
            slug="puma",
            is_active=True,
        )

        self.category = Category.objects.create(
            name="Sneakers",
            slug="sneakers",
            description="Casual and athletic sneakers.",
            is_active=True,
        )

        self.product = Product.objects.create(
            category=self.category,
            brand=self.brand,
            name="Puma Sneaker",
            slug="puma-sneaker",
            description="A pair of Puma sneakers.",
            is_active=True,
        )

        self.variant = ProductVariant.objects.create(
            product=self.product,
            name="White / Size 42",
            sku="PUMA-WHITE-42",
            attributes={
                "color": "White",
                "size": "42",
            },
            price=Decimal("40000.00"),
            is_active=True,
        )

        Inventory.objects.create(
            variant=self.variant,
            quantity=10,
            reserved_quantity=1,
        )

        self.list_url = reverse(
            "wishlist:wishlist-list-create",
        )

    def authenticate(self, user=None):
        self.client.force_authenticate(
            user=user or self.user,
        )

    def add_product(self, product=None):
        return self.client.post(
            self.list_url,
            {
                "product_id": (product or self.product).id,
            },
            format="json",
        )

    def test_unauthenticated_user_cannot_list_wishlist(self):
        response = self.client.get(self.list_url)

        self.assertEqual(
            response.status_code,
            status.HTTP_401_UNAUTHORIZED,
        )

    def test_unauthenticated_user_cannot_add_product(self):
        response = self.add_product()

        self.assertEqual(
            response.status_code,
            status.HTTP_401_UNAUTHORIZED,
        )
        self.assertEqual(
            WishlistItem.objects.count(),
            0,
        )

    def test_authenticated_user_can_view_empty_wishlist(self):
        self.authenticate()

        response = self.client.get(self.list_url)

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )
        self.assertEqual(response.data["count"], 0)
        self.assertEqual(response.data["results"], [])

    def test_user_can_add_active_product(self):
        self.authenticate()

        response = self.add_product()

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
        )
        self.assertEqual(
            WishlistItem.objects.count(),
            1,
        )

        wishlist_item = WishlistItem.objects.get()

        self.assertEqual(
            wishlist_item.user,
            self.user,
        )
        self.assertEqual(
            wishlist_item.product,
            self.product,
        )

        self.assertEqual(
            response.data["id"],
            wishlist_item.id,
        )
        self.assertEqual(
            response.data["product"]["id"],
            self.product.id,
        )
        self.assertEqual(
            response.data["product"]["name"],
            self.product.name,
        )
        self.assertEqual(
            response.data["product"]["slug"],
            self.product.slug,
        )
        self.assertEqual(
            response.data["product"]["starting_price"],
            "40000.00",
        )
        self.assertTrue(
            response.data["product"]["is_in_stock"],
        )
        self.assertTrue(
            response.data["product"]["is_available"],
        )
        self.assertIsNone(
            response.data["product"]["primary_image"],
        )

    def test_duplicate_addition_returns_existing_item(self):
        self.authenticate()

        first_response = self.add_product()
        second_response = self.add_product()

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
            WishlistItem.objects.count(),
            1,
        )

    def test_invalid_product_id_is_rejected(self):
        self.authenticate()

        response = self.client.post(
            self.list_url,
            {
                "product_id": 999999,
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )
        self.assertEqual(
            WishlistItem.objects.count(),
            0,
        )

    def test_inactive_product_cannot_be_added(self):
        self.product.is_active = False
        self.product.save(
            update_fields=["is_active"],
        )

        self.authenticate()

        response = self.add_product()

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )
        self.assertEqual(
            WishlistItem.objects.count(),
            0,
        )

    def test_product_in_inactive_category_cannot_be_added(self):
        self.category.is_active = False
        self.category.save(
            update_fields=["is_active"],
        )

        self.authenticate()

        response = self.add_product()

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )
        self.assertEqual(
            WishlistItem.objects.count(),
            0,
        )

    def test_product_with_inactive_brand_cannot_be_added(self):
        self.brand.is_active = False
        self.brand.save(
            update_fields=["is_active"],
        )

        self.authenticate()

        response = self.add_product()

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )
        self.assertEqual(
            WishlistItem.objects.count(),
            0,
        )

    def test_user_only_sees_own_wishlist_items(self):
        WishlistItem.objects.create(
            user=self.user,
            product=self.product,
        )

        WishlistItem.objects.create(
            user=self.other_user,
            product=self.product,
        )

        self.authenticate()

        response = self.client.get(self.list_url)

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )
        self.assertEqual(response.data["count"], 1)

        item_id = response.data["results"][0]["id"]

        self.assertEqual(
            item_id,
            WishlistItem.objects.get(
                user=self.user,
                product=self.product,
            ).id,
        )

    def test_user_cannot_delete_another_users_item(self):
        wishlist_item = WishlistItem.objects.create(
            user=self.user,
            product=self.product,
        )

        self.authenticate(self.other_user)

        delete_url = reverse(
            "wishlist:wishlist-item-delete",
            args=[wishlist_item.id],
        )

        response = self.client.delete(delete_url)

        self.assertEqual(
            response.status_code,
            status.HTTP_404_NOT_FOUND,
        )
        self.assertTrue(
            WishlistItem.objects.filter(
                pk=wishlist_item.pk,
            ).exists()
        )

    def test_owner_can_delete_wishlist_item(self):
        wishlist_item = WishlistItem.objects.create(
            user=self.user,
            product=self.product,
        )

        self.authenticate()

        delete_url = reverse(
            "wishlist:wishlist-item-delete",
            args=[wishlist_item.id],
        )

        response = self.client.delete(delete_url)

        self.assertEqual(
            response.status_code,
            status.HTTP_204_NO_CONTENT,
        )
        self.assertFalse(
            WishlistItem.objects.filter(
                pk=wishlist_item.pk,
            ).exists()
        )

    def test_saved_product_remains_visible_when_unavailable(self):
        wishlist_item = WishlistItem.objects.create(
            user=self.user,
            product=self.product,
        )

        self.product.is_active = False
        self.product.save(
            update_fields=["is_active"],
        )

        self.authenticate()

        response = self.client.get(self.list_url)

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )
        self.assertEqual(response.data["count"], 1)

        result = response.data["results"][0]

        self.assertEqual(
            result["id"],
            wishlist_item.id,
        )
        self.assertFalse(
            result["product"]["is_available"],
        )
        self.assertFalse(
            result["product"]["is_in_stock"],
        )
