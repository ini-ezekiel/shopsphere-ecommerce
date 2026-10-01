from django.shortcuts import get_object_or_404
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, generics, status
from rest_framework.permissions import (
    AllowAny,
    IsAuthenticated,
)
from rest_framework.response import Response
from dashboard.permissions import IsActiveStaff

from products.models import Product

from .models import Review
from .serializers import (
    CustomerReviewSerializer,
    PublicReviewSerializer,
    ReviewWriteSerializer,
    StaffReviewSerializer,
)


class ProductReviewListCreateView(
    generics.ListCreateAPIView,
):
    def get_product(self):
        if not hasattr(
            self,
            "_product",
        ):
            self._product = get_object_or_404(
                Product,
                slug=self.kwargs["product_slug"],
                is_active=True,
            )

        return self._product

    def get_permissions(self):
        if self.request.method == "GET":
            permission_classes = [
                AllowAny,
            ]
        else:
            permission_classes = [
                IsAuthenticated,
            ]

        return [permission() for permission in permission_classes]

    def get_throttles(self):
        if self.request.method == "POST":
            self.throttle_scope = "review_create"
        else:
            self.throttle_scope = "review_list"

        return super().get_throttles()

    def get_queryset(self):
        return (
            Review.objects.filter(
                product=self.get_product(),
                is_visible=True,
            )
            .select_related(
                "user",
                "product",
            )
            .order_by("-created_at")
        )

    def get_serializer_class(self):
        if self.request.method == "POST":
            return ReviewWriteSerializer

        return PublicReviewSerializer

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["product"] = self.get_product()

        return context

    def create(
        self,
        request,
        *args,
        **kwargs,
    ):
        serializer = self.get_serializer(
            data=request.data,
        )
        serializer.is_valid(
            raise_exception=True,
        )

        review = serializer.save()

        output_serializer = PublicReviewSerializer(
            review,
            context=self.get_serializer_context(),
        )

        return Response(
            output_serializer.data,
            status=status.HTTP_201_CREATED,
        )


class CustomerReviewListView(
    generics.ListAPIView,
):
    permission_classes = [
        IsAuthenticated,
    ]

    serializer_class = CustomerReviewSerializer
    throttle_scope = "review_manage"

    def get_queryset(self):
        return (
            Review.objects.filter(
                user=self.request.user,
            )
            .select_related(
                "product",
                "order_item__order",
            )
            .order_by("-created_at")
        )


class CustomerReviewDetailView(
    generics.RetrieveUpdateDestroyAPIView,
):
    permission_classes = [
        IsAuthenticated,
    ]

    serializer_class = CustomerReviewSerializer
    throttle_scope = "review_manage"

    def get_queryset(self):
        return Review.objects.filter(
            user=self.request.user,
        ).select_related(
            "product",
            "order_item__order",
            "order_item__variant__product",
        )


class StaffReviewListView(
    generics.ListAPIView,
):
    permission_classes = [
        IsAuthenticated,
        IsActiveStaff,
    ]

    throttle_scope = "staff_catalog"
    serializer_class = StaffReviewSerializer

    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]

    filterset_fields = [
        "is_visible",
        "rating",
        "product",
    ]

    search_fields = [
        "user__email",
        "user__username",
        "product__name",
        "product__slug",
        "order_item__order__order_number",
        "title",
        "comment",
    ]

    ordering_fields = [
        "rating",
        "created_at",
        "updated_at",
    ]

    ordering = [
        "-created_at",
    ]

    def get_queryset(self):
        return Review.objects.select_related(
            "user",
            "product",
            "order_item",
            "order_item__order",
        ).all()


class StaffReviewDetailView(
    generics.RetrieveUpdateAPIView,
):
    permission_classes = [
        IsAuthenticated,
        IsActiveStaff,
    ]

    throttle_scope = "staff_catalog"
    serializer_class = StaffReviewSerializer

    http_method_names = [
        "get",
        "patch",
        "head",
        "options",
    ]

    queryset = Review.objects.select_related(
        "user",
        "product",
        "order_item",
        "order_item__order",
    )
