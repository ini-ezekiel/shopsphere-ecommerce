import shutil
import tempfile

from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from io import BytesIO

from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import IntegrityError, transaction
from django.test import TestCase
from PIL import Image as PillowImage

from decimal import Decimal

from django.contrib.auth import get_user_model

User = get_user_model()

from .models import (
    Brand,
    Category,
    Inventory,
    Product,
    ProductImage,
    ProductVariant,
)


class ProductAPITests(APITestCase):
    def setUp(self):
        self.category = Category.objects.create(
            name="Sneakers",
            slug="sneakers",
            description="Sneaker products",
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
            description="White Puma sneakers",
        )
        self.variant = ProductVariant.objects.create(
            product=self.product,
            name="White / Size 42",
            sku="PUMA-WHT-42",
            attributes={
                "size": "42",
                "color": "White",
            },
            price="40000.00",
        )
        Inventory.objects.create(
            variant=self.variant,
            quantity=10,
            reserved_quantity=0,
        )

        self.cheaper_product = Product.objects.create(
            category=self.category,
            brand=self.brand,
            name="Puma Budget Sneaker",
            slug="puma-budget-sneaker",
            description="Affordable Puma sneakers",
        )
        self.cheaper_variant = ProductVariant.objects.create(
            product=self.cheaper_product,
            name="Black / Size 41",
            sku="PUMA-BLK-41",
            attributes={
                "size": "41",
                "color": "Black",
            },
            price="20000.00",
        )
        Inventory.objects.create(
            variant=self.cheaper_variant,
            quantity=0,
            reserved_quantity=0,
        )

        self.list_url = reverse("products:product-list")

    def test_public_can_list_products(self):
        response = self.client.get(self.list_url)

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )
        self.assertEqual(response.data["count"], 2)

    def test_product_detail_contains_variants(self):
        url = reverse(
            "products:product-detail",
            kwargs={"slug": self.product.slug},
        )

        response = self.client.get(url)

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )
        self.assertEqual(
            response.data["variants"][0]["sku"],
            self.variant.sku,
        )

    def test_filter_by_category(self):
        response = self.client.get(
            self.list_url,
            {"category": "sneakers"},
        )

        self.assertEqual(response.data["count"], 2)

    def test_filter_by_brand(self):
        response = self.client.get(
            self.list_url,
            {"brand": "puma"},
        )

        self.assertEqual(response.data["count"], 2)

    def test_filter_by_price_range(self):
        response = self.client.get(
            self.list_url,
            {
                "min_price": "30000",
                "max_price": "50000",
            },
        )

        self.assertEqual(response.data["count"], 1)
        self.assertEqual(
            response.data["results"][0]["id"],
            self.product.id,
        )

    def test_filter_in_stock_products(self):
        response = self.client.get(
            self.list_url,
            {"in_stock": "true"},
        )

        self.assertEqual(response.data["count"], 1)
        self.assertEqual(
            response.data["results"][0]["id"],
            self.product.id,
        )

    def test_search_products(self):
        response = self.client.get(
            self.list_url,
            {"search": "Budget"},
        )

        self.assertEqual(response.data["count"], 1)
        self.assertEqual(
            response.data["results"][0]["id"],
            self.cheaper_product.id,
        )

    def test_order_products_by_price(self):
        response = self.client.get(
            self.list_url,
            {"ordering": "catalog_price"},
        )

        results = response.data["results"]

        self.assertEqual(
            results[0]["id"],
            self.cheaper_product.id,
        )
        self.assertEqual(
            results[1]["id"],
            self.product.id,
        )

    def test_inactive_products_are_hidden(self):
        self.product.is_active = False
        self.product.save(update_fields=["is_active"])

        response = self.client.get(self.list_url)

        returned_ids = [product["id"] for product in response.data["results"]]

        self.assertNotIn(
            self.product.id,
            returned_ids,
        )

    def test_customers_cannot_create_products(self):
        response = self.client.post(
            self.list_url,
            {
                "name": "Unauthorized product",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_405_METHOD_NOT_ALLOWED,
        )


class ProductSecurityTests(TestCase):
    def setUp(self):
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
            description="White Puma sneakers",
        )
        self.variant = ProductVariant.objects.create(
            product=self.product,
            name="White / Size 42",
            sku="PUMA-WHT-42",
            attributes={
                "size": "42",
                "color": "White",
            },
            price="40000.00",
        )

    def create_test_image(
        self,
        width=400,
        height=400,
        filename="test.png",
    ):
        image_buffer = BytesIO()

        PillowImage.new(
            mode="RGB",
            size=(width, height),
            color="white",
        ).save(
            image_buffer,
            format="PNG",
        )

        return SimpleUploadedFile(
            filename,
            image_buffer.getvalue(),
            content_type="image/png",
        )

    def test_duplicate_variant_attributes_are_rejected(self):
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                ProductVariant.objects.create(
                    product=self.product,
                    name="Duplicate",
                    sku="PUMA-DUPLICATE",
                    attributes={
                        "size": "42",
                        "color": "White",
                    },
                    price="40000.00",
                )

    def test_discount_cannot_exceed_price(self):
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                ProductVariant.objects.create(
                    product=self.product,
                    name="Invalid discount",
                    sku="PUMA-INVALID-DISCOUNT",
                    attributes={
                        "size": "43",
                        "color": "White",
                    },
                    price="40000.00",
                    discount_price="50000.00",
                )

    def test_reserved_stock_cannot_exceed_quantity(self):
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Inventory.objects.create(
                    variant=self.variant,
                    quantity=5,
                    reserved_quantity=6,
                )

    def test_valid_image_passes_validation(self):
        product_image = ProductImage(
            product=self.product,
            image=self.create_test_image(),
            is_primary=True,
        )

        product_image.full_clean()

    def test_small_image_is_rejected(self):
        product_image = ProductImage(
            product=self.product,
            image=self.create_test_image(
                width=100,
                height=100,
            ),
        )

        with self.assertRaises(ValidationError):
            product_image.full_clean()

    def test_fake_image_is_rejected(self):
        fake_image = SimpleUploadedFile(
            "fake.jpg",
            b"This is not a real image.",
            content_type="image/jpeg",
        )
        product_image = ProductImage(
            product=self.product,
            image=fake_image,
        )

        with self.assertRaises(ValidationError):
            product_image.full_clean()

    def test_oversized_image_is_rejected(self):
        oversized_image = SimpleUploadedFile(
            "oversized.jpg",
            b"x" * (5 * 1024 * 1024 + 1),
            content_type="image/jpeg",
        )
        product_image = ProductImage(
            product=self.product,
            image=oversized_image,
        )

        with self.assertRaises(ValidationError):
            product_image.full_clean()


class StaffProductManagementAPITests(APITestCase):
    def setUp(self):
        self.staff_user = User.objects.create_user(
            username="product_staff",
            email="product-staff@example.com",
            password="StrongPassword123!",
            is_active=True,
            is_staff=True,
            is_email_verified=True,
        )

        self.customer = User.objects.create_user(
            username="product_customer",
            email="product-customer@example.com",
            password="StrongPassword123!",
            is_active=True,
            is_email_verified=True,
        )

        self.category = Category.objects.create(
            name="Staff Sneakers",
            slug="staff-sneakers",
            description="Staff product test category.",
        )

        self.brand = Brand.objects.create(
            name="Staff Brand",
            slug="staff-brand",
        )

        self.product = Product.objects.create(
            category=self.category,
            brand=self.brand,
            name="Staff Test Sneaker",
            slug="staff-test-sneaker",
            description="Staff product management test.",
            is_active=True,
        )

        self.variant = ProductVariant.objects.create(
            product=self.product,
            name="Black / Size 43",
            sku="STAFF-BLK-43",
            attributes={
                "color": "Black",
                "size": "43",
            },
            price=Decimal("25000.00"),
            discount_price=Decimal("22000.00"),
            is_active=True,
        )

        self.inventory = Inventory.objects.create(
            variant=self.variant,
            quantity=10,
            reserved_quantity=0,
        )

        self.product_list_url = reverse(
            "products_staff:product-list-create",
        )

        self.product_detail_url = reverse(
            "products_staff:product-detail",
            args=[self.product.pk],
        )

        self.variant_list_url = reverse(
            "products_staff:product-variant-list-create",
            args=[self.product.pk],
        )

        self.variant_detail_url = reverse(
            "products_staff:product-variant-detail",
            args=[self.variant.pk],
        )

        self.inventory_list_url = reverse(
            "products_staff:inventory-list",
        )

        self.inventory_detail_url = reverse(
            "products_staff:inventory-detail",
            args=[self.inventory.pk],
        )

    def authenticate(self, user=None):
        self.client.force_authenticate(
            user=user or self.staff_user,
        )

    def variant_payload(self, **overrides):
        payload = {
            "name": "White / Size 44",
            "sku": "STAFF-WHT-44",
            "attributes": {
                "color": "White",
                "size": "44",
            },
            "price": "27000.00",
            "discount_price": "24000.00",
            "is_active": True,
            "initial_quantity": 8,
        }

        payload.update(overrides)

        return payload

    def test_staff_product_list_requires_authentication(self):
        response = self.client.get(
            self.product_list_url,
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_401_UNAUTHORIZED,
        )

    def test_customer_cannot_access_staff_products(self):
        self.authenticate(self.customer)

        response = self.client.get(
            self.product_list_url,
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_403_FORBIDDEN,
        )

    def test_staff_can_list_products(self):
        self.authenticate()

        response = self.client.get(
            self.product_list_url,
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
            self.product.pk,
        )

    def test_staff_can_create_inactive_product(self):
        self.authenticate()

        response = self.client.post(
            self.product_list_url,
            {
                "name": "Inactive Staff Product",
                "slug": "inactive-staff-product",
                "description": "Created through the staff API.",
                "category_id": self.category.pk,
                "brand_id": None,
                "is_active": False,
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
        )

        self.assertFalse(
            response.data["is_active"],
        )

        self.assertFalse(
            response.data["is_in_stock"],
        )

        self.assertEqual(
            response.data["variant_count"],
            0,
        )

    def test_staff_can_create_variant_and_inventory(self):
        self.authenticate()

        response = self.client.post(
            self.variant_list_url,
            self.variant_payload(),
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
        )

        variant = ProductVariant.objects.get(
            sku="STAFF-WHT-44",
        )

        inventory = Inventory.objects.get(
            variant=variant,
        )

        self.assertEqual(
            variant.product_id,
            self.product.pk,
        )

        self.assertEqual(
            inventory.quantity,
            8,
        )

        self.assertEqual(
            inventory.reserved_quantity,
            0,
        )

        self.assertEqual(
            response.data["inventory"]["available_quantity"],
            8,
        )

    def test_product_id_is_not_required_when_creating_variant(self):
        self.authenticate()

        payload = self.variant_payload()

        self.assertNotIn(
            "product_id",
            payload,
        )

        response = self.client.post(
            self.variant_list_url,
            payload,
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
        )

    def test_duplicate_variant_attributes_are_rejected_by_api(self):
        self.authenticate()

        variant_count = ProductVariant.objects.count()
        inventory_count = Inventory.objects.count()

        response = self.client.post(
            self.variant_list_url,
            self.variant_payload(
                sku="STAFF-DUPLICATE-ATTRIBUTES",
                attributes={
                    "color": "Black",
                    "size": "43",
                },
            ),
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

        self.assertIn(
            "attributes",
            response.data,
        )

        self.assertEqual(
            ProductVariant.objects.count(),
            variant_count,
        )

        self.assertEqual(
            Inventory.objects.count(),
            inventory_count,
        )

    def test_duplicate_variant_sku_is_rejected_by_api(self):
        self.authenticate()

        response = self.client.post(
            self.variant_list_url,
            self.variant_payload(
                sku=self.variant.sku,
            ),
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

        self.assertIn(
            "sku",
            response.data,
        )

    def test_discount_above_price_is_rejected_by_api(self):
        self.authenticate()

        response = self.client.patch(
            self.variant_detail_url,
            {
                "discount_price": "30000.00",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

        self.assertIn(
            "discount_price",
            response.data,
        )

        self.variant.refresh_from_db()

        self.assertEqual(
            self.variant.discount_price,
            Decimal("22000.00"),
        )

    def test_staff_can_update_variant_price(self):
        self.authenticate()

        response = self.client.patch(
            self.variant_detail_url,
            {
                "price": "26000.00",
                "discount_price": "23000.00",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.assertEqual(
            response.data["current_price"],
            "23000.00",
        )

    def test_variant_cannot_be_moved_to_another_product(self):
        other_product = Product.objects.create(
            category=self.category,
            brand=self.brand,
            name="Other Product",
            slug="other-product",
            description="Another product.",
        )

        self.authenticate()

        response = self.client.patch(
            self.variant_detail_url,
            {
                "product_id": other_product.pk,
                "name": "Updated variant",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.variant.refresh_from_db()

        self.assertEqual(
            self.variant.product_id,
            self.product.pk,
        )

    def test_staff_can_filter_inventory_by_product(self):
        other_product = Product.objects.create(
            category=self.category,
            name="Inventory Other Product",
            slug="inventory-other-product",
            description="Another inventory product.",
        )

        other_variant = ProductVariant.objects.create(
            product=other_product,
            name="Default",
            sku="INVENTORY-OTHER",
            attributes={"type": "default"},
            price=Decimal("1000.00"),
        )

        Inventory.objects.create(
            variant=other_variant,
            quantity=3,
        )

        self.authenticate()

        response = self.client.get(
            self.inventory_list_url,
            {
                "product_id": self.product.pk,
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
            self.inventory.pk,
        )

    def test_staff_can_update_inventory_quantity(self):
        self.authenticate()

        response = self.client.patch(
            self.inventory_detail_url,
            {
                "quantity": 15,
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.assertEqual(
            response.data["quantity"],
            15,
        )

        self.assertEqual(
            response.data["available_quantity"],
            15,
        )

    def test_inventory_cannot_drop_below_reserved_quantity(self):
        self.inventory.reserved_quantity = 4
        self.inventory.save(
            update_fields=[
                "reserved_quantity",
                "updated_at",
            ]
        )

        self.authenticate()

        response = self.client.patch(
            self.inventory_detail_url,
            {
                "quantity": 3,
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

        self.assertIn(
            "quantity",
            response.data,
        )

        self.inventory.refresh_from_db()

        self.assertEqual(
            self.inventory.quantity,
            10,
        )

    def test_deactivated_product_is_hidden_publicly_but_visible_to_staff(self):
        self.authenticate()

        deactivate_response = self.client.patch(
            self.product_detail_url,
            {
                "is_active": False,
            },
            format="json",
        )

        self.assertEqual(
            deactivate_response.status_code,
            status.HTTP_200_OK,
        )

        public_url = reverse(
            "products:product-detail",
            kwargs={
                "slug": self.product.slug,
            },
        )

        self.client.force_authenticate(user=None)

        public_response = self.client.get(
            public_url,
        )

        self.assertEqual(
            public_response.status_code,
            status.HTTP_404_NOT_FOUND,
        )

        self.authenticate()

        staff_response = self.client.get(
            self.product_detail_url,
        )

        self.assertEqual(
            staff_response.status_code,
            status.HTTP_200_OK,
        )

        self.assertFalse(
            staff_response.data["is_active"],
        )


class StaffProductImageAPITests(APITestCase):
    def setUp(self):
        self.media_root = tempfile.mkdtemp(
            prefix="product-image-tests-",
        )

        self.media_settings = self.settings(
            MEDIA_ROOT=self.media_root,
        )
        self.media_settings.enable()

        self.addCleanup(
            self.media_settings.disable,
        )
        self.addCleanup(
            shutil.rmtree,
            self.media_root,
            True,
        )

        User = get_user_model()

        self.staff_user = User.objects.create_user(
            username="image_staff",
            email="image-staff@example.com",
            password="StrongPassword123!",
            is_active=True,
            is_staff=True,
            is_email_verified=True,
        )

        self.customer = User.objects.create_user(
            username="image_customer",
            email="image-customer@example.com",
            password="StrongPassword123!",
            is_active=True,
            is_email_verified=True,
        )

        self.category = Category.objects.create(
            name="Image Test Category",
            slug="image-test-category",
        )

        self.product = Product.objects.create(
            category=self.category,
            name="Image Test Product",
            slug="image-test-product",
            description="Product image API tests.",
            is_active=True,
        )

        self.image_list_url = reverse(
            "products_staff:product-image-list-create",
            args=[
                self.product.pk,
            ],
        )

    def authenticate(self, user=None):
        self.client.force_authenticate(
            user=user or self.staff_user,
        )

    def create_test_image(
        self,
        *,
        filename="test-image.png",
        width=400,
        height=400,
        color="black",
    ):
        image_buffer = BytesIO()

        PillowImage.new(
            mode="RGB",
            size=(
                width,
                height,
            ),
            color=color,
        ).save(
            image_buffer,
            format="PNG",
        )

        return SimpleUploadedFile(
            filename,
            image_buffer.getvalue(),
            content_type="image/png",
        )

    def upload_image(
        self,
        *,
        filename="test-image.png",
        is_primary=False,
        position=0,
        width=400,
        height=400,
        color="black",
    ):
        return self.client.post(
            self.image_list_url,
            {
                "image": self.create_test_image(
                    filename=filename,
                    width=width,
                    height=height,
                    color=color,
                ),
                "alt_text": "Product image",
                "is_primary": is_primary,
                "position": position,
            },
            format="multipart",
        )

    def test_image_list_requires_authentication(self):
        response = self.client.get(
            self.image_list_url,
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_401_UNAUTHORIZED,
        )

    def test_customer_cannot_manage_product_images(self):
        self.authenticate(
            self.customer,
        )

        response = self.client.get(
            self.image_list_url,
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_403_FORBIDDEN,
        )

    def test_first_image_is_automatically_primary(self):
        self.authenticate()

        response = self.upload_image(
            is_primary=False,
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
        )

        self.assertTrue(
            response.data["is_primary"],
        )

        product_image = ProductImage.objects.get(
            pk=response.data["id"],
        )

        self.assertTrue(
            product_image.is_primary,
        )

    def test_new_primary_image_demotes_previous_primary(self):
        self.authenticate()

        first_response = self.upload_image(
            filename="first.png",
            is_primary=False,
            position=0,
        )

        second_response = self.upload_image(
            filename="second.png",
            is_primary=True,
            position=1,
            color="white",
        )

        self.assertEqual(
            second_response.status_code,
            status.HTTP_201_CREATED,
        )

        first_image = ProductImage.objects.get(
            pk=first_response.data["id"],
        )

        second_image = ProductImage.objects.get(
            pk=second_response.data["id"],
        )

        self.assertFalse(
            first_image.is_primary,
        )

        self.assertTrue(
            second_image.is_primary,
        )

        self.assertEqual(
            ProductImage.objects.filter(
                product=self.product,
                is_primary=True,
            ).count(),
            1,
        )

    def test_primary_image_cannot_be_unset_directly(self):
        self.authenticate()

        create_response = self.upload_image()

        detail_url = reverse(
            "products_staff:product-image-detail",
            args=[
                create_response.data["id"],
            ],
        )

        response = self.client.patch(
            detail_url,
            {
                "is_primary": False,
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

        self.assertIn(
            "is_primary",
            response.data,
        )

        product_image = ProductImage.objects.get(
            pk=create_response.data["id"],
        )

        self.assertTrue(
            product_image.is_primary,
        )

    def test_deleting_primary_promotes_next_image(self):
        self.authenticate()

        first_response = self.upload_image(
            filename="first.png",
            position=0,
        )

        second_response = self.upload_image(
            filename="second.png",
            is_primary=True,
            position=1,
            color="white",
        )

        first_image = ProductImage.objects.get(
            pk=first_response.data["id"],
        )

        second_image = ProductImage.objects.get(
            pk=second_response.data["id"],
        )

        deleted_file_name = second_image.image.name
        storage = second_image.image.storage

        detail_url = reverse(
            "products_staff:product-image-detail",
            args=[
                second_image.pk,
            ],
        )

        with self.captureOnCommitCallbacks(
            execute=True,
        ):
            response = self.client.delete(
                detail_url,
            )

        self.assertEqual(
            response.status_code,
            status.HTTP_204_NO_CONTENT,
        )

        self.assertFalse(
            ProductImage.objects.filter(
                pk=second_image.pk,
            ).exists(),
        )

        first_image.refresh_from_db()

        self.assertTrue(
            first_image.is_primary,
        )

        self.assertFalse(
            storage.exists(
                deleted_file_name,
            )
        )

    def test_replacing_image_removes_previous_file(self):
        self.authenticate()

        create_response = self.upload_image(
            filename="original.png",
        )

        product_image = ProductImage.objects.get(
            pk=create_response.data["id"],
        )

        old_file_name = product_image.image.name
        storage = product_image.image.storage

        detail_url = reverse(
            "products_staff:product-image-detail",
            args=[
                product_image.pk,
            ],
        )

        with self.captureOnCommitCallbacks(
            execute=True,
        ):
            response = self.client.patch(
                detail_url,
                {
                    "image": self.create_test_image(
                        filename="replacement.png",
                        color="white",
                    ),
                    "alt_text": "Replacement image",
                },
                format="multipart",
            )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        product_image.refresh_from_db()

        self.assertTrue(
            product_image.is_primary,
        )

        self.assertNotEqual(
            product_image.image.name,
            old_file_name,
        )

        self.assertFalse(
            storage.exists(
                old_file_name,
            )
        )

        self.assertTrue(
            storage.exists(
                product_image.image.name,
            )
        )

    def test_invalid_image_content_is_rejected(self):
        self.authenticate()

        invalid_image = SimpleUploadedFile(
            "fake.jpg",
            b"This is not a real image.",
            content_type="image/jpeg",
        )

        response = self.client.post(
            self.image_list_url,
            {
                "image": invalid_image,
                "alt_text": "Invalid image",
                "is_primary": False,
                "position": 0,
            },
            format="multipart",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

        self.assertIn(
            "image",
            response.data,
        )

        self.assertEqual(
            ProductImage.objects.filter(
                product=self.product,
            ).count(),
            0,
        )

    def test_small_image_is_rejected_by_api(self):
        self.authenticate()

        response = self.upload_image(
            filename="small.png",
            width=100,
            height=100,
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

        self.assertIn(
            "image",
            response.data,
        )

        self.assertEqual(
            ProductImage.objects.filter(
                product=self.product,
            ).count(),
            0,
        )


class StaffCategoryBrandAPITests(APITestCase):
    def setUp(self):
        User = get_user_model()

        self.staff_user = User.objects.create_user(
            username="catalog_staff",
            email="catalog-staff@example.com",
            password="StrongPassword123!",
            is_active=True,
            is_staff=True,
            is_email_verified=True,
        )

        self.customer = User.objects.create_user(
            username="catalog_customer",
            email="catalog-customer@example.com",
            password="StrongPassword123!",
            is_active=True,
            is_email_verified=True,
        )

        self.category = Category.objects.create(
            name="Existing Category",
            slug="existing-category",
            description="Existing category.",
            is_active=True,
        )

        self.brand = Brand.objects.create(
            name="Existing Brand",
            slug="existing-brand",
            is_active=True,
        )

        self.product = Product.objects.create(
            category=self.category,
            brand=self.brand,
            name="Category Brand Product",
            slug="category-brand-product",
            description="Category and brand management test.",
            is_active=True,
        )

        self.category_list_url = reverse(
            "products_staff:category-list-create",
        )

        self.category_detail_url = reverse(
            "products_staff:category-detail",
            args=[
                self.category.pk,
            ],
        )

        self.brand_list_url = reverse(
            "products_staff:brand-list-create",
        )

        self.brand_detail_url = reverse(
            "products_staff:brand-detail",
            args=[
                self.brand.pk,
            ],
        )

    def authenticate(self, user=None):
        self.client.force_authenticate(
            user=user or self.staff_user,
        )

    def test_category_and_brand_management_require_authentication(self):
        for url in [
            self.category_list_url,
            self.brand_list_url,
        ]:
            with self.subTest(url=url):
                response = self.client.get(
                    url,
                )

                self.assertEqual(
                    response.status_code,
                    status.HTTP_401_UNAUTHORIZED,
                )

    def test_customer_cannot_manage_categories_or_brands(self):
        self.authenticate(
            self.customer,
        )

        for url in [
            self.category_list_url,
            self.brand_list_url,
        ]:
            with self.subTest(url=url):
                response = self.client.get(
                    url,
                )

                self.assertEqual(
                    response.status_code,
                    status.HTTP_403_FORBIDDEN,
                )

    def test_staff_can_create_category(self):
        self.authenticate()

        response = self.client.post(
            self.category_list_url,
            {
                "name": "Clothing",
                "slug": "clothing",
                "description": "Clothing products.",
                "is_active": True,
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
        )

        self.assertTrue(
            Category.objects.filter(
                name="Clothing",
                slug="clothing",
                is_active=True,
            ).exists(),
        )

    def test_staff_can_create_brand(self):
        self.authenticate()

        response = self.client.post(
            self.brand_list_url,
            {
                "name": "Nike",
                "slug": "nike",
                "is_active": True,
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
        )

        self.assertTrue(
            Brand.objects.filter(
                name="Nike",
                slug="nike",
                is_active=True,
            ).exists(),
        )

    def test_duplicate_category_and_brand_are_rejected(self):
        self.authenticate()

        category_response = self.client.post(
            self.category_list_url,
            {
                "name": self.category.name,
                "slug": self.category.slug,
                "description": "Duplicate category.",
                "is_active": True,
            },
            format="json",
        )

        brand_response = self.client.post(
            self.brand_list_url,
            {
                "name": self.brand.name,
                "slug": self.brand.slug,
                "is_active": True,
            },
            format="json",
        )

        self.assertEqual(
            category_response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

        self.assertIn(
            "name",
            category_response.data,
        )

        self.assertIn(
            "slug",
            category_response.data,
        )

        self.assertEqual(
            brand_response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

        self.assertIn(
            "name",
            brand_response.data,
        )

        self.assertIn(
            "slug",
            brand_response.data,
        )

    def test_deactivated_category_is_hidden_publicly_but_visible_to_staff(self):
        self.authenticate()

        response = self.client.patch(
            self.category_detail_url,
            {
                "is_active": False,
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.assertFalse(
            response.data["is_active"],
        )

        public_category_url = reverse(
            "products:category-list",
        )

        self.client.force_authenticate(
            user=None,
        )

        public_response = self.client.get(
            public_category_url,
        )

        public_ids = [category["id"] for category in public_response.data["results"]]

        self.assertNotIn(
            self.category.pk,
            public_ids,
        )

        self.authenticate()

        staff_response = self.client.get(
            self.category_detail_url,
        )

        self.assertEqual(
            staff_response.status_code,
            status.HTTP_200_OK,
        )

        self.assertFalse(
            staff_response.data["is_active"],
        )

    def test_deactivated_brand_hides_its_products_publicly(self):
        self.authenticate()

        response = self.client.patch(
            self.brand_detail_url,
            {
                "is_active": False,
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        public_product_url = reverse(
            "products:product-detail",
            kwargs={
                "slug": self.product.slug,
            },
        )

        self.client.force_authenticate(
            user=None,
        )

        public_response = self.client.get(
            public_product_url,
        )

        self.assertEqual(
            public_response.status_code,
            status.HTTP_404_NOT_FOUND,
        )

        self.authenticate()

        staff_product_url = reverse(
            "products_staff:product-detail",
            args=[
                self.product.pk,
            ],
        )

        staff_response = self.client.get(
            staff_product_url,
        )

        self.assertEqual(
            staff_response.status_code,
            status.HTTP_200_OK,
        )

    def test_categories_and_brands_cannot_be_deleted_through_api(self):
        self.authenticate()

        for url in [
            self.category_detail_url,
            self.brand_detail_url,
        ]:
            with self.subTest(url=url):
                response = self.client.delete(
                    url,
                )

                self.assertEqual(
                    response.status_code,
                    status.HTTP_405_METHOD_NOT_ALLOWED,
                )

        self.assertTrue(
            Category.objects.filter(
                pk=self.category.pk,
            ).exists(),
        )

        self.assertTrue(
            Brand.objects.filter(
                pk=self.brand.pk,
            ).exists(),
        )
