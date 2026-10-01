from rest_framework import serializers


class DashboardPeriodQuerySerializer(serializers.Serializer):
    period = serializers.ChoiceField(
        choices=[
            "today",
            "7d",
            "30d",
            "all",
        ],
        default="30d",
    )


class DashboardFinancialSummarySerializer(serializers.Serializer):
    currency = serializers.CharField()
    gross_paid_amount = serializers.DecimalField(
        max_digits=18,
        decimal_places=2,
    )
    processed_refund_amount = serializers.DecimalField(
        max_digits=18,
        decimal_places=2,
    )
    net_sales = serializers.DecimalField(
        max_digits=18,
        decimal_places=2,
    )


class DashboardOrderSummarySerializer(serializers.Serializer):
    total = serializers.IntegerField()
    pending_payment = serializers.IntegerField()
    confirmed = serializers.IntegerField()
    processing = serializers.IntegerField()
    shipped = serializers.IntegerField()
    delivered = serializers.IntegerField()
    cancelled = serializers.IntegerField()


class DashboardCatalogSummarySerializer(serializers.Serializer):
    active_products = serializers.IntegerField()
    active_variants = serializers.IntegerField()
    low_stock_variants = serializers.IntegerField()
    out_of_stock_variants = serializers.IntegerField()


class DashboardCustomerSummarySerializer(serializers.Serializer):
    total_customers = serializers.IntegerField()
    new_customers = serializers.IntegerField()


class DashboardRecentOrderSerializer(serializers.Serializer):
    order_number = serializers.CharField()
    customer_email = serializers.EmailField()
    status = serializers.CharField()
    status_display = serializers.CharField()
    total_amount = serializers.DecimalField(
        max_digits=18,
        decimal_places=2,
    )
    created_at = serializers.DateTimeField()


class DashboardRecentRefundSerializer(serializers.Serializer):
    reference = serializers.CharField()
    order_number = serializers.CharField()
    status = serializers.CharField()
    status_display = serializers.CharField()
    amount = serializers.DecimalField(
        max_digits=18,
        decimal_places=2,
    )
    created_at = serializers.DateTimeField()


class DashboardSummarySerializer(serializers.Serializer):
    period = serializers.CharField()
    period_start = serializers.DateTimeField(
        allow_null=True,
    )
    generated_at = serializers.DateTimeField()

    financial = DashboardFinancialSummarySerializer()
    orders = DashboardOrderSummarySerializer()
    catalog = DashboardCatalogSummarySerializer()
    customers = DashboardCustomerSummarySerializer()

    recent_orders = DashboardRecentOrderSerializer(
        many=True,
    )

    recent_refunds = DashboardRecentRefundSerializer(
        many=True,
    )
