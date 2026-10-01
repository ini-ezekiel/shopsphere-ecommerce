from django.db import transaction
from rest_framework import generics
from rest_framework.permissions import AllowAny, IsAuthenticated

from .models import DeliveryLocation, ShippingAddress
from .serializers import (
    DeliveryLocationSerializer,
    ShippingAddressSerializer,
)


class DeliveryLocationListView(generics.ListAPIView):
    serializer_class = DeliveryLocationSerializer
    permission_classes = [AllowAny]
    pagination_class = None

    def get_queryset(self):
        queryset = DeliveryLocation.objects.filter(
            is_active=True,
        ).order_by(
            "state",
            "city",
        )

        state = self.request.query_params.get("state")

        if state:
            queryset = queryset.filter(
                state__iexact=state.strip(),
            )

        return queryset


class ShippingAddressListCreateView(generics.ListCreateAPIView):
    serializer_class = ShippingAddressSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return (
            ShippingAddress.objects.filter(user=self.request.user)
            .select_related("delivery_location")
            .order_by("-is_default", "-updated_at")
        )


class ShippingAddressDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = ShippingAddressSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return ShippingAddress.objects.filter(user=self.request.user).select_related(
            "delivery_location"
        )

    def perform_destroy(self, instance):
        with transaction.atomic():
            addresses = list(
                ShippingAddress.objects.select_for_update()
                .filter(user=self.request.user)
                .order_by("-updated_at")
            )

            address = next(
                (item for item in addresses if item.pk == instance.pk),
                None,
            )

            if address is None:
                return

            was_default = address.is_default

            replacement = next(
                (item for item in addresses if item.pk != address.pk),
                None,
            )

            address.delete()

            if was_default and replacement is not None:
                ShippingAddress.objects.filter(
                    pk=replacement.pk,
                    user=self.request.user,
                ).update(is_default=True)
