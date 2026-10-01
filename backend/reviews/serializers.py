from rest_framework import serializers

from .models import Review
from .services import (
    ReviewError,
    create_verified_review,
)


class PublicReviewSerializer(serializers.ModelSerializer):
    reviewer_username = serializers.CharField(
        source="user.username",
        read_only=True,
    )

    product_slug = serializers.CharField(
        source="product.slug",
        read_only=True,
    )

    verified_purchase = serializers.SerializerMethodField()

    def get_verified_purchase(self, obj):
        return True

    class Meta:
        model = Review

        fields = [
            "id",
            "reviewer_username",
            "product_slug",
            "rating",
            "title",
            "comment",
            "verified_purchase",
            "created_at",
            "updated_at",
        ]

        read_only_fields = fields


class ReviewWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Review

        fields = [
            "rating",
            "title",
            "comment",
        ]

    def validate_title(self, value):
        return value.strip()

    def validate_comment(self, value):
        value = value.strip()

        if not value:
            raise serializers.ValidationError("A review comment is required.")

        return value

    def create(self, validated_data):
        request = self.context["request"]
        product = self.context["product"]

        try:
            return create_verified_review(
                user=request.user,
                product=product,
                rating=validated_data["rating"],
                title=validated_data.get(
                    "title",
                    "",
                ),
                comment=validated_data["comment"],
            )
        except ReviewError as error:
            raise serializers.ValidationError(
                {
                    "detail": error.message,
                }
            ) from error


class CustomerReviewSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(
        source="product.name",
        read_only=True,
    )

    product_slug = serializers.CharField(
        source="product.slug",
        read_only=True,
    )

    order_number = serializers.CharField(
        source="order_item.order.order_number",
        read_only=True,
    )

    class Meta:
        model = Review

        fields = [
            "id",
            "product_name",
            "product_slug",
            "order_number",
            "rating",
            "title",
            "comment",
            "is_visible",
            "created_at",
            "updated_at",
        ]

        read_only_fields = [
            "id",
            "product_name",
            "product_slug",
            "order_number",
            "is_visible",
            "created_at",
            "updated_at",
        ]

    def validate_title(self, value):
        return value.strip()

    def validate_comment(self, value):
        value = value.strip()

        if not value:
            raise serializers.ValidationError("A review comment is required.")

        return value


class StaffReviewSerializer(serializers.ModelSerializer):
    reviewer_id = serializers.IntegerField(
        source="user_id",
        read_only=True,
    )

    reviewer_username = serializers.CharField(
        source="user.username",
        read_only=True,
    )

    reviewer_email = serializers.EmailField(
        source="user.email",
        read_only=True,
    )

    product_id = serializers.IntegerField(
        read_only=True,
    )

    product_name = serializers.CharField(
        source="product.name",
        read_only=True,
    )

    product_slug = serializers.CharField(
        source="product.slug",
        read_only=True,
    )

    order_number = serializers.CharField(
        source="order_item.order.order_number",
        read_only=True,
    )

    verified_purchase = serializers.SerializerMethodField()

    def get_verified_purchase(self, obj):
        return True

    class Meta:
        model = Review

        fields = [
            "id",
            "reviewer_id",
            "reviewer_username",
            "reviewer_email",
            "product_id",
            "product_name",
            "product_slug",
            "order_number",
            "rating",
            "title",
            "comment",
            "verified_purchase",
            "is_visible",
            "created_at",
            "updated_at",
        ]

        read_only_fields = [
            "id",
            "reviewer_id",
            "reviewer_username",
            "reviewer_email",
            "product_id",
            "product_name",
            "product_slug",
            "order_number",
            "rating",
            "title",
            "comment",
            "verified_purchase",
            "created_at",
            "updated_at",
        ]
