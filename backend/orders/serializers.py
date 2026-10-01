from rest_framework import serializers

from addresses.models import ShippingAddress
from shipping.serializers import ShipmentSerializer

from .models import Order, OrderItem, OrderStatusHistory


class OrderAddressSerializer(serializers.Serializer):
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


class OrderItemSerializer(serializers.ModelSerializer):
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


class CustomerOrderStatusHistorySerializer(serializers.ModelSerializer):
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
            "note",
            "created_at",
        ]

        read_only_fields = fields


class OrderSerializer(serializers.ModelSerializer):
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

    delivery_address = OrderAddressSerializer(
        source="*",
        read_only=True,
    )

    items = OrderItemSerializer(
        many=True,
        read_only=True,
    )

    shipment = serializers.SerializerMethodField()

    status_history = CustomerOrderStatusHistorySerializer(
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
            "idempotency_key",
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
            "status_history",
            "created_at",
            "updated_at",
        ]

        read_only_fields = fields


class CheckoutSerializer(serializers.Serializer):
    idempotency_key = serializers.UUIDField()

    shipping_address_id = serializers.PrimaryKeyRelatedField(
        source="shipping_address",
        queryset=ShippingAddress.objects.none(),
        write_only=True,
        error_messages={
            "does_not_exist": ("The selected shipping address is unavailable."),
            "incorrect_type": ("The shipping address ID must be an integer."),
        },
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        request = self.context.get("request")

        if request is None or not request.user.is_authenticated:
            return

        self.fields["shipping_address_id"].queryset = ShippingAddress.objects.filter(
            user=request.user,
            delivery_location__is_active=True,
        ).select_related("delivery_location")
