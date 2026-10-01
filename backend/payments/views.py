import json

from django.shortcuts import get_object_or_404
from rest_framework import (
    filters,
    generics,
    status,
)
from rest_framework.permissions import (
    AllowAny,
    IsAuthenticated,
)
from rest_framework.response import Response
from rest_framework.views import APIView

from orders.models import Order

from .models import Refund
from .paystack import (
    PaystackConfigurationError,
    verify_webhook_signature,
)
from .permissions import IsActivePaymentStaff
from .serializers import (
    PaymentInitializationSerializer,
    PaymentSerializer,
    RefundInitiationSerializer,
    RefundSerializer,
)
from .services import (
    PaymentInitializationError,
    PaymentVerificationError,
    RefundProcessingError,
    WebhookProcessingError,
    initialize_order_payment,
    initiate_full_refund,
    process_paystack_webhook,
    verify_order_payment,
)


def customer_refund_queryset(user):
    return (
        Refund.objects.filter(
            payment__order__user=user,
        )
        .select_related(
            "payment",
            "payment__order",
        )
        .order_by("-created_at")
    )


class PaymentInitializeView(APIView):
    permission_classes = [IsAuthenticated]

    def get_object(self):
        return get_object_or_404(
            Order,
            user=self.request.user,
            order_number=(self.kwargs["order_number"]),
        )

    def post(
        self,
        request,
        order_number,
    ):
        order = self.get_object()

        if not request.user.is_email_verified:
            return Response(
                {"detail": ("Verify your email address before " "making a payment.")},
                status=status.HTTP_403_FORBIDDEN,
            )

        serializer = PaymentInitializationSerializer(
            data=request.data,
            context={
                "request": request,
            },
        )
        serializer.is_valid(raise_exception=True)

        try:
            payment, created = initialize_order_payment(
                user=request.user,
                order_number=order.order_number,
                idempotency_key=(serializer.validated_data["idempotency_key"]),
            )
        except PaymentInitializationError as error:
            return Response(
                {
                    "detail": error.message,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        output_serializer = PaymentSerializer(
            payment,
            context={
                "request": request,
            },
        )

        response_status = status.HTTP_201_CREATED if created else status.HTTP_200_OK

        return Response(
            output_serializer.data,
            status=response_status,
        )


class PaymentVerifyView(APIView):
    permission_classes = [IsAuthenticated]

    def post(
        self,
        request,
        reference,
    ):
        if not request.user.is_email_verified:
            return Response(
                {
                    "detail": (
                        "Verify your email address before " "verifying a payment."
                    )
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        try:
            payment, finalized = verify_order_payment(
                user=request.user,
                reference=reference,
            )
        except PaymentVerificationError as error:
            return Response(
                {
                    "detail": error.message,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        output_serializer = PaymentSerializer(
            payment,
            context={
                "request": request,
            },
        )

        response_data = dict(
            output_serializer.data,
        )
        response_data["finalized"] = finalized

        return Response(
            response_data,
            status=status.HTTP_200_OK,
        )


class StaffRefundInitiateView(APIView):
    permission_classes = [
        IsAuthenticated,
        IsActivePaymentStaff,
    ]

    throttle_scope = "refund_staff"

    def post(
        self,
        request,
        reference,
    ):
        serializer = RefundInitiationSerializer(
            data=request.data,
            context={
                "request": request,
            },
        )
        serializer.is_valid(raise_exception=True)

        try:
            refund, initiated = initiate_full_refund(
                payment_reference=reference,
                requested_by=request.user,
                reason=(serializer.validated_data["reason"]),
            )
        except RefundProcessingError as error:
            return Response(
                {
                    "detail": error.message,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        refund = Refund.objects.select_related(
            "payment",
            "payment__order",
        ).get(pk=refund.pk)

        output_serializer = RefundSerializer(
            refund,
            context={
                "request": request,
            },
        )

        response_data = dict(
            output_serializer.data,
        )
        response_data["initiated"] = initiated

        return Response(
            response_data,
            status=(status.HTTP_201_CREATED if initiated else status.HTTP_200_OK),
        )


class StaffRefundListView(
    generics.ListAPIView,
):
    permission_classes = [
        IsAuthenticated,
        IsActivePaymentStaff,
    ]

    serializer_class = RefundSerializer
    throttle_scope = "refund_read"

    filter_backends = [
        filters.SearchFilter,
        filters.OrderingFilter,
    ]

    search_fields = [
        "reference",
        "payment__reference",
        "payment__order__order_number",
        "payment__order__user__email",
        "reason",
    ]

    ordering_fields = [
        "amount",
        "created_at",
        "updated_at",
        "processed_at",
    ]

    ordering = [
        "-created_at",
    ]

    def get_queryset(self):
        queryset = Refund.objects.select_related(
            "payment",
            "payment__order",
            "payment__order__user",
        ).all()

        refund_status = self.request.query_params.get(
            "status",
            "",
        ).strip()

        provider = self.request.query_params.get(
            "provider",
            "",
        ).strip()

        if refund_status:
            queryset = queryset.filter(
                status=refund_status,
            )

        if provider:
            queryset = queryset.filter(
                provider=provider,
            )

        return queryset


class CustomerRefundListView(
    generics.ListAPIView,
):
    permission_classes = [IsAuthenticated]
    serializer_class = RefundSerializer
    throttle_scope = "refund_read"

    def get_queryset(self):
        return customer_refund_queryset(
            self.request.user,
        )


class CustomerRefundDetailView(
    generics.RetrieveAPIView,
):
    permission_classes = [IsAuthenticated]
    serializer_class = RefundSerializer
    throttle_scope = "refund_read"
    lookup_field = "reference"
    lookup_url_kwarg = "reference"

    def get_queryset(self):
        return customer_refund_queryset(
            self.request.user,
        )


class PaystackWebhookView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request):
        raw_body = request.body

        signature = request.headers.get(
            "x-paystack-signature",
            "",
        )

        try:
            signature_is_valid = verify_webhook_signature(
                raw_body=raw_body,
                signature=signature,
            )
        except PaystackConfigurationError as error:
            return Response(
                {
                    "detail": str(error),
                },
                status=(status.HTTP_503_SERVICE_UNAVAILABLE),
            )

        if not signature_is_valid:
            return Response(
                {
                    "detail": ("Invalid Paystack signature."),
                },
                status=status.HTTP_401_UNAUTHORIZED,
            )

        try:
            payload = json.loads(raw_body.decode("utf-8"))
        except (
            UnicodeDecodeError,
            json.JSONDecodeError,
        ):
            return Response(
                {
                    "detail": ("Invalid webhook payload."),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not isinstance(payload, dict):
            return Response(
                {
                    "detail": ("The webhook payload must be " "a JSON object."),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            event, finalized = process_paystack_webhook(
                payload=payload,
                raw_body=raw_body,
            )
        except WebhookProcessingError as error:
            return Response(
                {
                    "detail": error.message,
                },
                status=(status.HTTP_503_SERVICE_UNAVAILABLE),
            )

        return Response(
            {
                "detail": "Webhook received.",
                "event_id": event.id,
                "processed": event.processed,
                "finalized": finalized,
            },
            status=status.HTTP_200_OK,
        )
