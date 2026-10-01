from rest_framework import serializers
from payments.serializers import PaymentSerializer

from orders.models import (
    Order,
    OrderItem,
    OrderStatusHistory,
)

from .models import Shipment


class ShipmentSerializer(serializers.ModelSerializer):
    status_display = serializers.CharField(
        source="get_status_display",
        read_only=True,
    )

    class Meta:
        model = Shipment

        fields = [
            "status",
            "status_display",
            "carrier",
            "tracking_number",
            "shipped_at",
            "delivered_at",
            "created_at",
            "updated_at",
        ]

        read_only_fields = fields


class OrderStatusHistorySerializer(serializers.ModelSerializer):
    from_status_display = serializers.CharField(
        source="get_from_status_display",
        read_only=True,
    )

    to_status_display = serializers.CharField(
        source="get_to_status_display",
        read_only=True,
    )

    class Meta:
        model = OrderStatusHistory

        fields = [
            "id",
            "from_status",
            "from_status_display",
            "to_status",
            "to_status_display",
            "changed_by_email",
            "note",
            "created_at",
        ]

        read_only_fields = fields


class StaffOrderItemSerializer(serializers.ModelSerializer):
    variant_id = serializers.IntegerField(
        read_only=True,
        allow_null=True,
    )

    class Meta:
        model = OrderItem

        fields = [
            "id",
            "variant_id",
            "product_name",
            "variant_name",
            "sku",
            "attributes",
            "unit_price",
            "quantity",
            "line_total",
            "created_at",
        ]

        read_only_fields = fields


class StaffOrderAddressSerializer(serializers.Serializer):
    recipient_name = serializers.CharField(read_only=True)
    phone_number = serializers.CharField(read_only=True)
    address_line_1 = serializers.CharField(read_only=True)
    address_line_2 = serializers.CharField(read_only=True)
    landmark = serializers.CharField(read_only=True)
    postal_code = serializers.CharField(read_only=True)
    city = serializers.CharField(read_only=True)
    state = serializers.CharField(read_only=True)
    country = serializers.CharField(read_only=True)

    estimated_delivery_days = serializers.IntegerField(
        read_only=True,
    )


class FulfillmentTransitionSerializer(serializers.Serializer):
    status = serializers.ChoiceField(
        choices=[
            Order.Status.PROCESSING,
            Order.Status.SHIPPED,
            Order.Status.DELIVERED,
        ],
    )

    note = serializers.CharField(
        required=False,
        allow_blank=True,
        max_length=2000,
        default="",
    )

    carrier = serializers.CharField(
        required=False,
        allow_blank=True,
        max_length=100,
        default="",
    )

    tracking_number = serializers.CharField(
        required=False,
        allow_blank=True,
        max_length=100,
        default="",
    )

    def validate(self, attrs):
        new_status = attrs["status"]

        carrier = attrs.get(
            "carrier",
            "",
        ).strip()

        tracking_number = attrs.get(
            "tracking_number",
            "",
        ).strip()

        if new_status == Order.Status.SHIPPED:
            if not carrier:
                raise serializers.ValidationError(
                    {"carrier": ("A carrier is required when shipping an order.")}
                )

            if not tracking_number:
                raise serializers.ValidationError(
                    {
                        "tracking_number": (
                            "A tracking number is required when " "shipping an order."
                        )
                    }
                )

        elif carrier or tracking_number:
            raise serializers.ValidationError(
                "Carrier and tracking information may only "
                "be supplied when marking an order as shipped."
            )

        attrs["carrier"] = carrier
        attrs["tracking_number"] = tracking_number
        attrs["note"] = attrs.get(
            "note",
            "",
        ).strip()

        return attrs


class StaffOrderListSerializer(serializers.ModelSerializer):
    customer_email = serializers.EmailField(
        source="user.email",
        read_only=True,
    )

    status_display = serializers.CharField(
        source="get_status_display",
        read_only=True,
    )

    inventory_status_display = serializers.CharField(
        source="get_inventory_status_display",
        read_only=True,
    )

    shipment = serializers.SerializerMethodField()

    def get_shipment(self, obj):
        shipment = getattr(
            obj,
            "shipment",
            None,
        )

        if shipment is None:
            return None

        return ShipmentSerializer(
            shipment,
            context=self.context,
        ).data

    class Meta:
        model = Order

        fields = [
            "id",
            "order_number",
            "customer_email",
            "recipient_name",
            "status",
            "status_display",
            "inventory_status",
            "inventory_status_display",
            "currency",
            "total_amount",
            "shipment",
            "created_at",
            "updated_at",
        ]

        read_only_fields = fields


class FulfillmentOrderSerializer(serializers.ModelSerializer):
    customer_email = serializers.EmailField(
        source="user.email",
        read_only=True,
    )

    status_display = serializers.CharField(
        source="get_status_display",
        read_only=True,
    )

    inventory_status_display = serializers.CharField(
        source="get_inventory_status_display",
        read_only=True,
    )

    cancellation_reason_display = serializers.CharField(
        source="get_cancellation_reason_display",
        read_only=True,
        allow_null=True,
    )

    shipping_address_id = serializers.IntegerField(
        read_only=True,
        allow_null=True,
    )

    delivery_address = StaffOrderAddressSerializer(
        source="*",
        read_only=True,
    )

    items = StaffOrderItemSerializer(
        many=True,
        read_only=True,
    )

    shipment = serializers.SerializerMethodField()

    status_history = OrderStatusHistorySerializer(
        many=True,
        read_only=True,
    )

    payments = PaymentSerializer(
        many=True,
        read_only=True,
    )

    def get_shipment(self, obj):
        shipment = getattr(
            obj,
            "shipment",
            None,
        )

        if shipment is None:
            return None

        return ShipmentSerializer(
            shipment,
            context=self.context,
        ).data

    class Meta:
        model = Order

        fields = [
            "id",
            "order_number",
            "customer_email",
            "status",
            "status_display",
            "inventory_status",
            "inventory_status_display",
            "shipping_address_id",
            "delivery_address",
            "currency",
            "subtotal",
            "discount_amount",
            "shipping_fee",
            "total_amount",
            "reservation_expires_at",
            "cancelled_at",
            "cancellation_reason",
            "cancellation_reason_display",
            "items",
            "shipment",
            "payments",
            "status_history",
            "created_at",
            "updated_at",
        ]

        read_only_fields = fields
