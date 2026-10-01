from django.db.models import Prefetch
from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from products.models import ProductVariant

from .models import WishlistItem
from .serializers import WishlistItemSerializer


def customer_wishlist_queryset(user):
    active_variants = (
        ProductVariant.objects.filter(
            is_active=True,
        )
        .select_related("inventory")
        .order_by("price")
    )

    return (
        WishlistItem.objects.filter(
            user=user,
        )
        .select_related(
            "product",
            "product__category",
            "product__brand",
        )
        .prefetch_related(
            "product__images",
            Prefetch(
                "product__variants",
                queryset=active_variants,
                to_attr="active_wishlist_variants",
            ),
        )
        .order_by("-created_at")
    )


class WishlistListCreateView(
    generics.ListCreateAPIView,
):
    permission_classes = [IsAuthenticated]
    serializer_class = WishlistItemSerializer

    def get_queryset(self):
        return customer_wishlist_queryset(
            self.request.user,
        )

    def get_throttles(self):
        if self.request.method == "GET":
            self.throttle_scope = "wishlist_read"
        else:
            self.throttle_scope = "wishlist_write"

        return super().get_throttles()

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(
            data=request.data,
        )
        serializer.is_valid(raise_exception=True)

        wishlist_item = serializer.save()
        created = serializer.created

        wishlist_item = self.get_queryset().get(
            pk=wishlist_item.pk,
        )

        output_serializer = self.get_serializer(
            wishlist_item,
        )

        return Response(
            output_serializer.data,
            status=(status.HTTP_201_CREATED if created else status.HTTP_200_OK),
        )


class WishlistItemDeleteView(
    generics.DestroyAPIView,
):
    permission_classes = [IsAuthenticated]
    serializer_class = WishlistItemSerializer
    throttle_scope = "wishlist_write"

    def get_queryset(self):
        return customer_wishlist_queryset(
            self.request.user,
        )
