from rest_framework import serializers

from .models import (
    Payment,
    Refund,
)


class PaymentInitializationSerializer(
    serializers.Serializer,
):
    idempotency_key = serializers.UUIDField()


class RefundInitiationSerializer(
    serializers.Serializer,
):
    reason = serializers.CharField(
        max_length=1000,
        min_length=5,
        trim_whitespace=True,
    )

    def validate_reason(self, value):
        value = value.strip()

        if not value:
            raise serializers.ValidationError("A refund reason is required.")

        return value


class RefundSerializer(
    serializers.ModelSerializer,
):
    payment_reference = serializers.CharField(
        source="payment.reference",
        read_only=True,
    )

    order_number = serializers.CharField(
        source="payment.order.order_number",
        read_only=True,
    )

    status_display = serializers.CharField(
        source="get_status_display",
        read_only=True,
    )

    provider_display = serializers.CharField(
        source="get_provider_display",
        read_only=True,
    )

    class Meta:
        model = Refund

        fields = [
            "id",
            "reference",
            "payment_reference",
            "order_number",
            "provider",
            "provider_display",
            "status",
            "status_display",
            "provider_status",
            "amount",
            "amount_subunit",
            "currency",
            "reason",
            "processed_at",
            "created_at",
            "updated_at",
        ]

        read_only_fields = fields


class PaymentSerializer(
    serializers.ModelSerializer,
):
    order_number = serializers.CharField(
        source="order.order_number",
        read_only=True,
    )

    status_display = serializers.CharField(
        source="get_status_display",
        read_only=True,
    )

    provider_display = serializers.CharField(
        source="get_provider_display",
        read_only=True,
    )

    refund = serializers.SerializerMethodField()

    def get_refund(self, obj):
        refund = getattr(
            obj,
            "refund",
            None,
        )

        if refund is None:
            return None

        return RefundSerializer(
            refund,
            context=self.context,
        ).data

    class Meta:
        model = Payment

        fields = [
            "id",
            "order_number",
            "provider",
            "provider_display",
            "reference",
            "idempotency_key",
            "status",
            "status_display",
            "provider_status",
            "amount",
            "amount_subunit",
            "currency",
            "authorization_url",
            "access_code",
            "channel",
            "gateway_response",
            "paid_at",
            "verified_at",
            "refund",
            "created_at",
            "updated_at",
        ]

        read_only_fields = fields
