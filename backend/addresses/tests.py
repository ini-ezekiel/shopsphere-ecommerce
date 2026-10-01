from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from .models import DeliveryLocation, ShippingAddress

User = get_user_model()


class AddressAPITests(APITestCase):
    def setUp(self):
        cache.clear()

        self.user = User.objects.create_user(
            username="address_user",
            email="address@example.com",
            password="StrongPassword123!",
            is_email_verified=True,
        )

        self.other_user = User.objects.create_user(
            username="other_address_user",
            email="otheraddress@example.com",
            password="StrongPassword123!",
            is_email_verified=True,
        )

        self.uyo = DeliveryLocation.objects.create(
            state="Akwa Ibom",
            city="Uyo",
            shipping_fee=Decimal("2500.00"),
            estimated_delivery_days=2,
            is_active=True,
        )

        self.ikot_ekpene = DeliveryLocation.objects.create(
            state="Akwa Ibom",
            city="Ikot Ekpene",
            shipping_fee=Decimal("2500.00"),
            estimated_delivery_days=2,
            is_active=True,
        )

        self.lagos = DeliveryLocation.objects.create(
            state="Lagos",
            city="Ikeja",
            shipping_fee=Decimal("4000.00"),
            estimated_delivery_days=5,
            is_active=True,
        )

        self.inactive_location = DeliveryLocation.objects.create(
            state="Akwa Ibom",
            city="Inactive City",
            shipping_fee=Decimal("2500.00"),
            estimated_delivery_days=2,
            is_active=False,
        )

        self.location_url = reverse("delivery-location-list")
        self.address_list_url = reverse("shipping-address-list")

    def tearDown(self):
        cache.clear()

    def authenticate(self, user=None):
        self.client.force_authenticate(user=user or self.user)

    def address_payload(self, location=None, **overrides):
        payload = {
            "label": "home",
            "recipient_name": "Test Customer",
            "phone_number": "08012345678",
            "address_line_1": "12 Example Street",
            "address_line_2": "",
            "landmark": "Near Example Junction",
            "postal_code": "520101",
            "delivery_location_id": (location or self.uyo).id,
            "is_default": False,
        }

        payload.update(overrides)
        return payload

    def create_address(self, location=None, **overrides):
        return self.client.post(
            self.address_list_url,
            self.address_payload(
                location=location,
                **overrides,
            ),
            format="json",
        )

    def test_delivery_locations_are_public(self):
        response = self.client.get(self.location_url)

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )
        self.assertEqual(len(response.data), 3)

        returned_ids = {location["id"] for location in response.data}

        self.assertNotIn(
            self.inactive_location.id,
            returned_ids,
        )

    def test_delivery_locations_can_be_filtered_by_state(self):
        response = self.client.get(
            self.location_url,
            {"state": "akwa ibom"},
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )
        self.assertEqual(len(response.data), 2)

        returned_states = {location["state"] for location in response.data}

        self.assertEqual(
            returned_states,
            {"Akwa Ibom"},
        )

    def test_shipping_addresses_require_authentication(self):
        response = self.client.get(self.address_list_url)

        self.assertEqual(
            response.status_code,
            status.HTTP_401_UNAUTHORIZED,
        )

    def test_first_address_becomes_default(self):
        self.authenticate()

        response = self.create_address()

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
        )
        self.assertTrue(response.data["is_default"])

        address = ShippingAddress.objects.get(pk=response.data["id"])
        self.assertTrue(address.is_default)

    def test_second_address_is_not_default_automatically(self):
        self.authenticate()

        first_response = self.create_address()
        second_response = self.create_address(
            location=self.ikot_ekpene,
            label="work",
            address_line_1="25 Market Road",
        )

        self.assertEqual(
            first_response.status_code,
            status.HTTP_201_CREATED,
        )
        self.assertEqual(
            second_response.status_code,
            status.HTTP_201_CREATED,
        )
        self.assertTrue(first_response.data["is_default"])
        self.assertFalse(second_response.data["is_default"])

        self.assertEqual(
            ShippingAddress.objects.filter(
                user=self.user,
                is_default=True,
            ).count(),
            1,
        )

    def test_user_can_change_default_address(self):
        self.authenticate()

        first_response = self.create_address()
        second_response = self.create_address(
            location=self.ikot_ekpene,
            label="work",
        )

        second_url = reverse(
            "shipping-address-detail",
            args=[second_response.data["id"]],
        )

        response = self.client.patch(
            second_url,
            {"is_default": True},
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )
        self.assertTrue(response.data["is_default"])

        first_address = ShippingAddress.objects.get(pk=first_response.data["id"])
        second_address = ShippingAddress.objects.get(pk=second_response.data["id"])

        self.assertFalse(first_address.is_default)
        self.assertTrue(second_address.is_default)

    def test_current_default_cannot_be_unset_directly(self):
        self.authenticate()

        create_response = self.create_address()

        address_url = reverse(
            "shipping-address-detail",
            args=[create_response.data["id"]],
        )

        response = self.client.patch(
            address_url,
            {"is_default": False},
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

        address = ShippingAddress.objects.get(pk=create_response.data["id"])
        self.assertTrue(address.is_default)

    def test_user_only_sees_their_own_addresses(self):
        ShippingAddress.objects.create(
            user=self.other_user,
            delivery_location=self.lagos,
            label="home",
            recipient_name="Other Customer",
            phone_number="08098765432",
            address_line_1="10 Other Street",
            is_default=True,
        )

        self.authenticate()
        own_response = self.create_address()

        response = self.client.get(self.address_list_url)

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        results = response.data["results"]
        returned_ids = {address["id"] for address in results}

        self.assertEqual(
            returned_ids,
            {own_response.data["id"]},
        )

    def test_user_cannot_access_another_users_address(self):
        other_address = ShippingAddress.objects.create(
            user=self.other_user,
            delivery_location=self.lagos,
            label="home",
            recipient_name="Other Customer",
            phone_number="08098765432",
            address_line_1="10 Other Street",
            is_default=True,
        )

        self.authenticate()

        address_url = reverse(
            "shipping-address-detail",
            args=[other_address.id],
        )

        get_response = self.client.get(address_url)
        patch_response = self.client.patch(
            address_url,
            {"label": "work"},
            format="json",
        )
        delete_response = self.client.delete(address_url)

        self.assertEqual(
            get_response.status_code,
            status.HTTP_404_NOT_FOUND,
        )
        self.assertEqual(
            patch_response.status_code,
            status.HTTP_404_NOT_FOUND,
        )
        self.assertEqual(
            delete_response.status_code,
            status.HTTP_404_NOT_FOUND,
        )
        self.assertTrue(ShippingAddress.objects.filter(pk=other_address.id).exists())

    def test_deleting_default_promotes_remaining_address(self):
        self.authenticate()

        first_response = self.create_address()
        second_response = self.create_address(
            location=self.ikot_ekpene,
            label="work",
        )

        first_url = reverse(
            "shipping-address-detail",
            args=[first_response.data["id"]],
        )

        response = self.client.delete(first_url)

        self.assertEqual(
            response.status_code,
            status.HTTP_204_NO_CONTENT,
        )
        self.assertFalse(
            ShippingAddress.objects.filter(pk=first_response.data["id"]).exists()
        )

        second_address = ShippingAddress.objects.get(pk=second_response.data["id"])
        self.assertTrue(second_address.is_default)

    def test_inactive_delivery_location_is_rejected(self):
        self.authenticate()

        response = self.create_address(location=self.inactive_location)

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )
        self.assertIn(
            "delivery_location_id",
            response.data,
        )

    def test_invalid_phone_number_is_rejected(self):
        self.authenticate()

        response = self.create_address(phone_number="12345")

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )
        self.assertIn(
            "phone_number",
            response.data,
        )
