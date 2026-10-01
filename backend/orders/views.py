from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import Order
from .serializers import CheckoutSerializer, OrderSerializer
from .services import (
    CheckoutError,
    OrderCancellationError,
    cancel_pending_order,
    create_checkout_order,
)


class CheckoutView(generics.GenericAPIView):
    serializer_class = CheckoutSerializer
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        if not request.user.is_email_verified:
            return Response(
                {"detail": ("Verify your email address before checkout.")},
                status=status.HTTP_403_FORBIDDEN,
            )

        serializer = self.get_serializer(
            data=request.data,
        )
        serializer.is_valid(raise_exception=True)

        try:
            order, created = create_checkout_order(
                user=request.user,
                shipping_address=(serializer.validated_data["shipping_address"]),
                idempotency_key=(serializer.validated_data["idempotency_key"]),
            )
        except CheckoutError as error:
            return Response(
                {
                    "detail": error.message,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        output_serializer = OrderSerializer(
            order,
            context=self.get_serializer_context(),
        )

        response_status = status.HTTP_201_CREATED if created else status.HTTP_200_OK

        return Response(
            output_serializer.data,
            status=response_status,
        )


class OrderListView(generics.ListAPIView):
    serializer_class = OrderSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return (
            Order.objects.filter(user=self.request.user)
            .select_related("shipping_address", "shipment",)
            .prefetch_related("items", "status_history",)
            .order_by("-created_at")
        )


class OrderDetailView(generics.RetrieveAPIView):
    serializer_class = OrderSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = "order_number"
    lookup_url_kwarg = "order_number"

    def get_queryset(self):
        return (
            Order.objects.filter(user=self.request.user)
            .select_related("shipping_address")
            .prefetch_related("items")
        )


class OrderCancelView(generics.GenericAPIView):
    serializer_class = OrderSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = "order_number"
    lookup_url_kwarg = "order_number"

    def get_queryset(self):
        return Order.objects.filter(user=self.request.user).prefetch_related("items")

    def post(self, request, *args, **kwargs):
        owned_order = self.get_object()

        try:
            order, _cancelled = cancel_pending_order(
                user=request.user,
                order_number=owned_order.order_number,
            )
        except OrderCancellationError as error:
            return Response(
                {
                    "detail": error.message,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        output_serializer = self.get_serializer(
            order,
        )

        return Response(
            output_serializer.data,
            status=status.HTTP_200_OK,
        )
