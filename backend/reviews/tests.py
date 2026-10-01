from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.cache import cache
from rest_framework import status
from rest_framework.test import APITestCase

from orders.models import Order, OrderItem
from products.models import (
    Category,
    Product,
    ProductVariant,
)

from .models import Review

User = get_user_model()


class ReviewAPITests(APITestCase):
    password = "StrongPass123!"

    def setUp(self):
        cache.clear()

        self.category = Category.objects.create(
            name="Sneakers",
            slug="sneakers",
            description="Casual and athletic sneakers.",
            is_active=True,
        )

        self.product = Product.objects.create(
            category=self.category,
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

        self.customer = self.create_user(
            email="customer@example.com",
            username="customer",
            verified=True,
        )

        self.other_customer = self.create_user(
            email="other@example.com",
            username="other_customer",
            verified=True,
        )

        self.unverified_customer = self.create_user(
            email="unverified@example.com",
            username="unverified_customer",
            verified=False,
        )

        self.order, self.order_item = self.create_order(
            user=self.customer,
            status_value=Order.Status.DELIVERED,
            inventory_status=Order.InventoryStatus.COMMITTED,
        )

        self.product_reviews_url = (
            f"/api/v1/catalog/products/{self.product.slug}/reviews/"
        )
        self.customer_reviews_url = "/api/v1/reviews/me/"
        self.product_detail_url = f"/api/v1/catalog/products/{self.product.slug}/"

        self.valid_payload = {
            "rating": 5,
            "title": "Excellent sneakers",
            "comment": (
                "The sneakers matched the description and " "arrived in good condition."
            ),
        }

    def create_user(
        self,
        *,
        email,
        username,
        verified,
    ):
        return User.objects.create_user(
            email=email,
            username=username,
            password=self.password,
            is_email_verified=verified,
        )

    def create_order(
        self,
        *,
        user,
        status_value,
        inventory_status,
    ):
        order = Order.objects.create(
            user=user,
            status=status_value,
            inventory_status=inventory_status,
            recipient_name="Test Customer",
            phone_number="08012345678",
            address_line_1="12 Example Street",
            address_line_2="",
            landmark="Near Example Junction",
            postal_code="520101",
            city="Uyo",
            state="Akwa Ibom",
            country="Nigeria",
            estimated_delivery_days=2,
            subtotal=Decimal("40000.00"),
            discount_amount=Decimal("0.00"),
            shipping_fee=Decimal("2500.00"),
            total_amount=Decimal("42500.00"),
        )

        order_item = OrderItem.objects.create(
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

        return order, order_item

    def authenticate(self, user):
        self.client.force_authenticate(user=user)

    def create_review(self):
        self.authenticate(self.customer)

        response = self.client.post(
            self.product_reviews_url,
            self.valid_payload,
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
        )

        return Review.objects.get(
            user=self.customer,
            product=self.product,
        )

    def test_public_can_list_visible_reviews(self):
        review = self.create_review()

        self.client.force_authenticate(user=None)

        response = self.client.get(
            self.product_reviews_url,
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )
        self.assertEqual(response.data["count"], 1)

        result = response.data["results"][0]

        self.assertEqual(result["id"], review.id)
        self.assertEqual(
            result["reviewer_username"],
            self.customer.username,
        )
        self.assertEqual(
            result["product_slug"],
            self.product.slug,
        )
        self.assertTrue(result["verified_purchase"])

        self.assertNotIn("user", result)
        self.assertNotIn("customer_email", result)
        self.assertNotIn("order_number", result)
        self.assertNotIn("is_visible", result)

    def test_unauthenticated_customer_cannot_create_review(self):
        response = self.client.post(
            self.product_reviews_url,
            self.valid_payload,
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_401_UNAUTHORIZED,
        )
        self.assertEqual(Review.objects.count(), 0)

    def test_unverified_customer_cannot_create_review(self):
        self.create_order(
            user=self.unverified_customer,
            status_value=Order.Status.DELIVERED,
            inventory_status=Order.InventoryStatus.COMMITTED,
        )

        self.authenticate(self.unverified_customer)

        response = self.client.post(
            self.product_reviews_url,
            self.valid_payload,
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )
        self.assertEqual(Review.objects.count(), 0)

    def test_customer_without_delivered_purchase_cannot_review(self):
        self.authenticate(self.other_customer)

        response = self.client.post(
            self.product_reviews_url,
            self.valid_payload,
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )
        self.assertEqual(Review.objects.count(), 0)

    def test_customer_with_undelivered_order_cannot_review(self):
        self.create_order(
            user=self.other_customer,
            status_value=Order.Status.CONFIRMED,
            inventory_status=Order.InventoryStatus.COMMITTED,
        )

        self.authenticate(self.other_customer)

        response = self.client.post(
            self.product_reviews_url,
            self.valid_payload,
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )
        self.assertEqual(Review.objects.count(), 0)

    def test_delivered_customer_can_create_review(self):
        self.authenticate(self.customer)

        response = self.client.post(
            self.product_reviews_url,
            self.valid_payload,
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
        )
        self.assertEqual(Review.objects.count(), 1)

        review = Review.objects.get()

        self.assertEqual(review.user, self.customer)
        self.assertEqual(review.product, self.product)
        self.assertEqual(review.order_item, self.order_item)
        self.assertEqual(review.rating, 5)
        self.assertTrue(review.is_visible)

    def test_customer_cannot_review_product_twice(self):
        self.create_review()

        response = self.client.post(
            self.product_reviews_url,
            {
                "rating": 4,
                "title": "Another review",
                "comment": "Trying to submit another review.",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )
        self.assertEqual(Review.objects.count(), 1)

    def test_rating_must_be_between_one_and_five(self):
        self.authenticate(self.customer)

        for invalid_rating in [0, 6]:
            with self.subTest(rating=invalid_rating):
                response = self.client.post(
                    self.product_reviews_url,
                    {
                        "rating": invalid_rating,
                        "title": "Invalid rating",
                        "comment": "Testing an invalid rating.",
                    },
                    format="json",
                )

                self.assertEqual(
                    response.status_code,
                    status.HTTP_400_BAD_REQUEST,
                )

        self.assertEqual(Review.objects.count(), 0)

    def test_blank_review_comment_is_rejected(self):
        self.authenticate(self.customer)

        response = self.client.post(
            self.product_reviews_url,
            {
                "rating": 5,
                "title": "Test title",
                "comment": "   ",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )
        self.assertEqual(Review.objects.count(), 0)

    def test_customer_can_list_own_reviews(self):
        review = self.create_review()

        response = self.client.get(
            self.customer_reviews_url,
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )
        self.assertEqual(response.data["count"], 1)

        result = response.data["results"][0]

        self.assertEqual(result["id"], review.id)
        self.assertEqual(
            result["product_name"],
            self.product.name,
        )
        self.assertEqual(
            result["product_slug"],
            self.product.slug,
        )
        self.assertEqual(
            result["order_number"],
            self.order.order_number,
        )
        self.assertTrue(result["is_visible"])

    def test_customer_can_update_own_review(self):
        review = self.create_review()

        detail_url = f"/api/v1/reviews/{review.id}/"

        response = self.client.patch(
            detail_url,
            {
                "rating": 4,
                "title": "  Very good sneakers  ",
                "comment": "  The sneakers were very good.  ",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        review.refresh_from_db()

        self.assertEqual(review.rating, 4)
        self.assertEqual(
            review.title,
            "Very good sneakers",
        )
        self.assertEqual(
            review.comment,
            "The sneakers were very good.",
        )

    def test_customer_can_delete_own_review(self):
        review = self.create_review()

        detail_url = f"/api/v1/reviews/{review.id}/"

        response = self.client.delete(detail_url)

        self.assertEqual(
            response.status_code,
            status.HTTP_204_NO_CONTENT,
        )
        self.assertFalse(Review.objects.filter(pk=review.pk).exists())

    def test_customer_cannot_update_another_users_review(self):
        review = self.create_review()

        self.authenticate(self.other_customer)

        detail_url = f"/api/v1/reviews/{review.id}/"

        response = self.client.patch(
            detail_url,
            {
                "rating": 1,
                "comment": "Unauthorized update attempt.",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_404_NOT_FOUND,
        )

        review.refresh_from_db()

        self.assertEqual(review.rating, 5)
        self.assertEqual(
            review.comment,
            self.valid_payload["comment"],
        )

    def test_customer_cannot_delete_another_users_review(self):
        review = self.create_review()

        self.authenticate(self.other_customer)

        detail_url = f"/api/v1/reviews/{review.id}/"

        response = self.client.delete(detail_url)

        self.assertEqual(
            response.status_code,
            status.HTTP_404_NOT_FOUND,
        )
        self.assertTrue(Review.objects.filter(pk=review.pk).exists())

    def test_hidden_review_is_not_public_but_remains_for_owner(self):
        review = self.create_review()

        Review.objects.filter(pk=review.pk).update(
            is_visible=False,
        )

        self.client.force_authenticate(user=None)

        public_response = self.client.get(
            self.product_reviews_url,
        )

        self.assertEqual(
            public_response.status_code,
            status.HTTP_200_OK,
        )
        self.assertEqual(public_response.data["count"], 0)

        self.authenticate(self.customer)

        owner_response = self.client.get(
            self.customer_reviews_url,
        )

        self.assertEqual(
            owner_response.status_code,
            status.HTTP_200_OK,
        )
        self.assertEqual(owner_response.data["count"], 1)
        self.assertFalse(owner_response.data["results"][0]["is_visible"])

    def test_product_detail_contains_review_statistics(self):
        self.create_review()

        self.client.force_authenticate(user=None)

        response = self.client.get(
            self.product_detail_url,
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )
        self.assertEqual(
            response.data["average_rating"],
            "5.00",
        )
        self.assertEqual(
            response.data["review_count"],
            1,
        )

    def test_product_statistics_use_only_visible_reviews(self):
        review = self.create_review()

        Review.objects.filter(pk=review.pk).update(
            is_visible=False,
        )

        self.client.force_authenticate(user=None)

        response = self.client.get(
            self.product_detail_url,
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )
        self.assertIsNone(
            response.data["average_rating"],
        )
        self.assertEqual(
            response.data["review_count"],
            0,
        )

    def test_product_statistics_calculate_average_rating(self):
        self.create_review()

        second_order, second_order_item = self.create_order(
            user=self.other_customer,
            status_value=Order.Status.DELIVERED,
            inventory_status=Order.InventoryStatus.COMMITTED,
        )

        self.authenticate(self.other_customer)

        response = self.client.post(
            self.product_reviews_url,
            {
                "rating": 3,
                "title": "Good sneakers",
                "comment": "The product was good overall.",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
        )

        self.client.force_authenticate(user=None)

        response = self.client.get(
            self.product_detail_url,
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )
        self.assertEqual(
            response.data["average_rating"],
            "4.00",
        )
        self.assertEqual(
            response.data["review_count"],
            2,
        )


class StaffReviewModerationAPITests(APITestCase):
    password = "StrongPass123!"

    create_user = ReviewAPITests.create_user
    create_order = ReviewAPITests.create_order
    authenticate = ReviewAPITests.authenticate

    def setUp(self):
        self.category = Category.objects.create(
            name="Moderation Category",
            slug="moderation-category",
            description="Review moderation tests.",
            is_active=True,
        )

        self.product = Product.objects.create(
            category=self.category,
            name="Moderation Product",
            slug="moderation-product",
            description="Review moderation product.",
            is_active=True,
        )

        self.variant = ProductVariant.objects.create(
            product=self.product,
            name="Default Variant",
            sku="MODERATION-VARIANT",
            attributes={
                "type": "default",
            },
            price=Decimal("10000.00"),
            is_active=True,
        )

        self.customer = self.create_user(
            email="moderation-customer@example.com",
            username="moderation_customer",
            verified=True,
        )

        self.staff_user = User.objects.create_user(
            email="moderation-staff@example.com",
            username="moderation_staff",
            password=self.password,
            is_active=True,
            is_staff=True,
            is_email_verified=True,
        )

        self.order, self.order_item = self.create_order(
            user=self.customer,
            status_value=Order.Status.DELIVERED,
            inventory_status=Order.InventoryStatus.COMMITTED,
        )

        self.review = Review.objects.create(
            user=self.customer,
            product=self.product,
            order_item=self.order_item,
            rating=4,
            title="Very good product",
            comment="The product matched its description.",
            is_visible=True,
        )

        self.staff_list_url = "/api/v1/staff/reviews/"

        self.staff_detail_url = f"/api/v1/staff/reviews/{self.review.pk}/"

        self.public_reviews_url = (
            f"/api/v1/catalog/products/" f"{self.product.slug}/reviews/"
        )

        self.product_detail_url = f"/api/v1/catalog/products/" f"{self.product.slug}/"

    def test_staff_review_list_requires_authentication(self):
        response = self.client.get(
            self.staff_list_url,
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_401_UNAUTHORIZED,
        )

    def test_customer_cannot_access_review_moderation(self):
        self.authenticate(
            self.customer,
        )

        response = self.client.get(
            self.staff_list_url,
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_403_FORBIDDEN,
        )

    def test_staff_can_list_reviews_with_moderation_details(self):
        self.authenticate(
            self.staff_user,
        )

        response = self.client.get(
            self.staff_list_url,
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.assertEqual(
            response.data["count"],
            1,
        )

        result = response.data["results"][0]

        self.assertEqual(
            result["id"],
            self.review.pk,
        )

        self.assertEqual(
            result["reviewer_email"],
            self.customer.email,
        )

        self.assertEqual(
            result["product_id"],
            self.product.pk,
        )

        self.assertEqual(
            result["order_number"],
            self.order.order_number,
        )

        self.assertTrue(
            result["verified_purchase"],
        )

    def test_staff_can_filter_and_search_reviews(self):
        self.review.is_visible = False
        self.review.save(
            update_fields=[
                "is_visible",
                "updated_at",
            ]
        )

        self.authenticate(
            self.staff_user,
        )

        filtered_response = self.client.get(
            self.staff_list_url,
            {
                "is_visible": "false",
                "rating": 4,
                "product": self.product.pk,
            },
        )

        self.assertEqual(
            filtered_response.status_code,
            status.HTTP_200_OK,
        )

        self.assertEqual(
            filtered_response.data["count"],
            1,
        )

        search_response = self.client.get(
            self.staff_list_url,
            {
                "search": self.customer.email,
            },
        )

        self.assertEqual(
            search_response.status_code,
            status.HTTP_200_OK,
        )

        self.assertEqual(
            search_response.data["count"],
            1,
        )

    def test_staff_can_hide_review_from_public_catalogue(self):
        self.authenticate(
            self.staff_user,
        )

        response = self.client.patch(
            self.staff_detail_url,
            {
                "is_visible": False,
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.assertFalse(
            response.data["is_visible"],
        )

        self.client.force_authenticate(
            user=None,
        )

        public_response = self.client.get(
            self.public_reviews_url,
        )

        self.assertEqual(
            public_response.status_code,
            status.HTTP_200_OK,
        )

        self.assertEqual(
            public_response.data["count"],
            0,
        )

        product_response = self.client.get(
            self.product_detail_url,
        )

        self.assertEqual(
            product_response.status_code,
            status.HTTP_200_OK,
        )

        self.assertIsNone(
            product_response.data["average_rating"],
        )

        self.assertEqual(
            product_response.data["review_count"],
            0,
        )

    def test_staff_can_restore_hidden_review(self):
        self.review.is_visible = False
        self.review.save(
            update_fields=[
                "is_visible",
                "updated_at",
            ]
        )

        self.authenticate(
            self.staff_user,
        )

        response = self.client.patch(
            self.staff_detail_url,
            {
                "is_visible": True,
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.assertTrue(
            response.data["is_visible"],
        )

        self.client.force_authenticate(
            user=None,
        )

        public_response = self.client.get(
            self.public_reviews_url,
        )

        self.assertEqual(
            public_response.data["count"],
            1,
        )

    def test_staff_cannot_rewrite_customer_review_content(self):
        self.authenticate(
            self.staff_user,
        )

        response = self.client.patch(
            self.staff_detail_url,
            {
                "rating": 1,
                "title": "Changed by staff",
                "comment": "Staff changed the review.",
                "is_visible": False,
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.review.refresh_from_db()

        self.assertEqual(
            self.review.rating,
            4,
        )

        self.assertEqual(
            self.review.title,
            "Very good product",
        )

        self.assertEqual(
            self.review.comment,
            "The product matched its description.",
        )

        self.assertFalse(
            self.review.is_visible,
        )

    def test_staff_cannot_delete_or_replace_review(self):
        self.authenticate(
            self.staff_user,
        )

        delete_response = self.client.delete(
            self.staff_detail_url,
        )

        put_response = self.client.put(
            self.staff_detail_url,
            {
                "is_visible": False,
            },
            format="json",
        )

        self.assertEqual(
            delete_response.status_code,
            status.HTTP_405_METHOD_NOT_ALLOWED,
        )

        self.assertEqual(
            put_response.status_code,
            status.HTTP_405_METHOD_NOT_ALLOWED,
        )

        self.assertTrue(
            Review.objects.filter(
                pk=self.review.pk,
            ).exists(),
        )
