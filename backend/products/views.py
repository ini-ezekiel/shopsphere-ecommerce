from django.conf import settings
from django.db import transaction
from django.db.models import (
    Avg,
    Count,
    DecimalField,
    Exists,
    ExpressionWrapper,
    F,
    IntegerField,
    Min,
    OuterRef,
    Prefetch,
    Q,
    Subquery,
    Value,
)
from django.db.models.functions import Coalesce
from django.shortcuts import get_object_or_404
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, generics, status, serializers
from rest_framework.parsers import (
    FormParser,
    JSONParser,
    MultiPartParser,
)
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from dashboard.permissions import IsActiveStaff
from reviews.models import Review

from .filters import ProductFilter
from .models import (
    Category,
    Brand,
    Inventory,
    Product,
    ProductImage,
    ProductVariant,
)
from .serializers import (
    BrandSerializer,
    CategorySerializer,
    ProductDetailSerializer,
    ProductListSerializer,
    StaffInventorySerializer,
    StaffInventoryUpdateSerializer,
    StaffProductSerializer,
    StaffProductVariantSerializer,
    StaffProductVariantWriteSerializer,
    StaffProductWriteSerializer,
    StaffProductImageSerializer,
    StaffBrandSerializer,
    StaffCategorySerializer,
)


def active_product_queryset():
    active_variants = ProductVariant.objects.filter(
        is_active=True,
    ).select_related(
        "inventory",
    )

    available_variants = ProductVariant.objects.filter(
        product_id=OuterRef("pk"),
        is_active=True,
        inventory__quantity__gt=F("inventory__reserved_quantity"),
    )

    visible_review_statistics = (
        Review.objects.filter(
            product_id=OuterRef("pk"),
            is_visible=True,
        )
        .values(
            "product_id",
        )
        .annotate(
            average=Avg("rating"),
            total=Count("id"),
        )
    )

    return (
        Product.objects.filter(
            is_active=True,
            category__is_active=True,
        )
        .filter(Q(brand__isnull=True) | Q(brand__is_active=True))
        .annotate(
            catalog_price=Min(
                Coalesce(
                    "variants__discount_price",
                    "variants__price",
                    output_field=DecimalField(
                        max_digits=12,
                        decimal_places=2,
                    ),
                ),
                filter=Q(
                    variants__is_active=True,
                ),
            ),
            has_available_stock=Exists(
                available_variants,
            ),
            average_rating=Subquery(
                visible_review_statistics.values(
                    "average",
                )[:1],
                output_field=DecimalField(
                    max_digits=3,
                    decimal_places=2,
                ),
            ),
            review_count=Coalesce(
                Subquery(
                    visible_review_statistics.values(
                        "total",
                    )[:1],
                    output_field=IntegerField(),
                ),
                Value(0),
            ),
        )
        .select_related(
            "category",
            "brand",
        )
        .prefetch_related(
            "images",
            Prefetch(
                "variants",
                queryset=active_variants,
                to_attr="active_variants",
            ),
        )
    )


def staff_product_queryset():
    variants = ProductVariant.objects.select_related(
        "inventory",
    ).order_by(
        "id",
    )

    return (
        Product.objects.select_related(
            "category",
            "brand",
        )
        .prefetch_related(
            "images",
            Prefetch(
                "variants",
                queryset=variants,
            ),
        )
        .order_by(
            "-created_at",
        )
    )


class BrandListView(generics.ListAPIView):
    permission_classes = [
        AllowAny,
    ]

    serializer_class = BrandSerializer
    queryset = Brand.objects.filter(
        is_active=True,
    ).order_by(
        "name",
    )


class CategoryListView(generics.ListAPIView):
    permission_classes = [
        AllowAny,
    ]

    serializer_class = CategorySerializer
    queryset = Category.objects.filter(
        is_active=True,
    ).order_by(
        "name",
    )


class ProductListView(generics.ListAPIView):
    permission_classes = [
        AllowAny,
    ]

    serializer_class = ProductListSerializer
    queryset = active_product_queryset()

    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]

    filterset_class = ProductFilter

    search_fields = [
        "name",
        "description",
        "brand__name",
        "=variants__sku",
    ]

    ordering_fields = [
        "name",
        "created_at",
        "catalog_price",
        "average_rating",
        "review_count",
    ]

    ordering = [
        "-created_at",
    ]


class ProductDetailView(generics.RetrieveAPIView):
    permission_classes = [
        AllowAny,
    ]

    serializer_class = ProductDetailSerializer
    lookup_field = "slug"
    queryset = active_product_queryset()


class StaffProductListCreateView(generics.ListCreateAPIView):
    permission_classes = [
        IsAuthenticated,
        IsActiveStaff,
    ]

    throttle_scope = "staff_catalog"

    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]

    filterset_fields = [
        "is_active",
        "category",
        "brand",
    ]

    search_fields = [
        "name",
        "description",
        "slug",
        "brand__name",
        "variants__sku",
    ]

    ordering_fields = [
        "name",
        "created_at",
        "updated_at",
    ]

    ordering = [
        "-created_at",
    ]

    def get_queryset(self):
        return staff_product_queryset()

    def get_serializer_class(self):
        if self.request.method == "POST":
            return StaffProductWriteSerializer

        return StaffProductSerializer

    @transaction.atomic
    def create(self, request, *args, **kwargs):
        input_serializer = StaffProductWriteSerializer(
            data=request.data,
            context=self.get_serializer_context(),
        )
        input_serializer.is_valid(raise_exception=True)

        product = input_serializer.save()

        product = staff_product_queryset().get(
            pk=product.pk,
        )

        output_serializer = StaffProductSerializer(
            product,
            context=self.get_serializer_context(),
        )

        return Response(
            output_serializer.data,
            status=status.HTTP_201_CREATED,
        )


class StaffProductDetailView(generics.RetrieveUpdateAPIView):
    permission_classes = [
        IsAuthenticated,
        IsActiveStaff,
    ]

    throttle_scope = "staff_catalog"

    def get_queryset(self):
        return staff_product_queryset()

    def get_serializer_class(self):
        if self.request.method in {
            "PUT",
            "PATCH",
        }:
            return StaffProductWriteSerializer

        return StaffProductSerializer

    @transaction.atomic
    def update(self, request, *args, **kwargs):
        partial = kwargs.pop(
            "partial",
            False,
        )

        product = self.get_object()

        input_serializer = StaffProductWriteSerializer(
            product,
            data=request.data,
            partial=partial,
            context=self.get_serializer_context(),
        )
        input_serializer.is_valid(raise_exception=True)

        product = input_serializer.save()

        product = staff_product_queryset().get(
            pk=product.pk,
        )

        output_serializer = StaffProductSerializer(
            product,
            context=self.get_serializer_context(),
        )

        return Response(
            output_serializer.data,
            status=status.HTTP_200_OK,
        )


class StaffProductVariantListCreateView(
    generics.ListCreateAPIView,
):
    permission_classes = [
        IsAuthenticated,
        IsActiveStaff,
    ]

    throttle_scope = "staff_catalog"

    filter_backends = [
        filters.SearchFilter,
        filters.OrderingFilter,
    ]

    search_fields = [
        "name",
        "sku",
    ]

    ordering_fields = [
        "name",
        "sku",
        "price",
        "created_at",
    ]

    ordering = [
        "id",
    ]

    def get_product(self):
        return get_object_or_404(
            Product,
            pk=self.kwargs["product_pk"],
        )

    def get_queryset(self):
        return ProductVariant.objects.filter(
            product_id=self.kwargs["product_pk"],
        ).select_related(
            "product",
            "inventory",
        )

    def get_serializer_class(self):
        if self.request.method == "POST":
            return StaffProductVariantWriteSerializer

        return StaffProductVariantSerializer

    @transaction.atomic
    def create(self, request, *args, **kwargs):
        product = self.get_product()

        input_serializer = StaffProductVariantWriteSerializer(
            data=request.data,
            context={
                **self.get_serializer_context(),
                "product": product,
            },
        )
        input_serializer.is_valid(raise_exception=True)

        variant_data = dict(
            input_serializer.validated_data,
        )

        initial_quantity = variant_data.pop(
            "initial_quantity",
            0,
        )

        variant_data.pop(
            "product",
            None,
        )

        variant = ProductVariant.objects.create(
            product=product,
            **variant_data,
        )

        Inventory.objects.create(
            variant=variant,
            quantity=initial_quantity,
            reserved_quantity=0,
        )

        variant = ProductVariant.objects.select_related(
            "product",
            "inventory",
        ).get(pk=variant.pk)

        output_serializer = StaffProductVariantSerializer(
            variant,
            context=self.get_serializer_context(),
        )

        return Response(
            output_serializer.data,
            status=status.HTTP_201_CREATED,
        )


class StaffProductVariantDetailView(
    generics.RetrieveUpdateAPIView,
):
    permission_classes = [
        IsAuthenticated,
        IsActiveStaff,
    ]

    throttle_scope = "staff_catalog"

    queryset = ProductVariant.objects.select_related(
        "product",
        "inventory",
    )

    def get_serializer_class(self):
        if self.request.method in {
            "PUT",
            "PATCH",
        }:
            return StaffProductVariantWriteSerializer

        return StaffProductVariantSerializer

    @transaction.atomic
    def update(self, request, *args, **kwargs):
        partial = kwargs.pop(
            "partial",
            False,
        )

        variant = self.get_object()

        input_serializer = StaffProductVariantWriteSerializer(
            variant,
            data=request.data,
            partial=partial,
            context=self.get_serializer_context(),
        )
        input_serializer.is_valid(raise_exception=True)

        variant = input_serializer.save()

        variant = ProductVariant.objects.select_related(
            "product",
            "inventory",
        ).get(pk=variant.pk)

        output_serializer = StaffProductVariantSerializer(
            variant,
            context=self.get_serializer_context(),
        )

        return Response(
            output_serializer.data,
            status=status.HTTP_200_OK,
        )


class StaffInventoryListView(generics.ListAPIView):
    permission_classes = [
        IsAuthenticated,
        IsActiveStaff,
    ]

    throttle_scope = "staff_catalog"
    serializer_class = StaffInventorySerializer

    filter_backends = [
        filters.SearchFilter,
        filters.OrderingFilter,
    ]

    search_fields = [
        "variant__sku",
        "variant__name",
        "variant__product__name",
    ]

    ordering_fields = [
        "quantity",
        "reserved_quantity",
        "available_quantity_value",
        "updated_at",
    ]

    ordering = [
        "variant__product__name",
        "variant__sku",
    ]

    def get_queryset(self):
        queryset = Inventory.objects.select_related(
            "variant",
            "variant__product",
        ).annotate(
            available_quantity_value=(
                ExpressionWrapper(
                    F("quantity") - F("reserved_quantity"),
                    output_field=IntegerField(),
                )
            )
        )

        product_id = self.request.query_params.get(
            "product_id",
        )

        if product_id:
            queryset = queryset.filter(
                variant__product_id=product_id,
            )

        stock_status = self.request.query_params.get(
            "stock_status",
        )

        low_stock_threshold = getattr(
            settings,
            "DASHBOARD_LOW_STOCK_THRESHOLD",
            5,
        )

        if stock_status == "out_of_stock":
            queryset = queryset.filter(
                available_quantity_value__lte=0,
            )
        elif stock_status == "low_stock":
            queryset = queryset.filter(
                available_quantity_value__gt=0,
                available_quantity_value__lte=(low_stock_threshold),
            )
        elif stock_status == "in_stock":
            queryset = queryset.filter(
                available_quantity_value__gt=0,
            )

        return queryset


class StaffInventoryDetailView(
    generics.RetrieveUpdateAPIView,
):
    permission_classes = [
        IsAuthenticated,
        IsActiveStaff,
    ]

    throttle_scope = "staff_catalog"

    queryset = Inventory.objects.select_related(
        "variant",
        "variant__product",
    )

    def get_serializer_class(self):
        if self.request.method in {
            "PUT",
            "PATCH",
        }:
            return StaffInventoryUpdateSerializer

        return StaffInventorySerializer

    @transaction.atomic
    def update(self, request, *args, **kwargs):
        partial = kwargs.pop(
            "partial",
            False,
        )

        inventory = get_object_or_404(
            Inventory.objects.select_for_update().select_related(
                "variant",
                "variant__product",
            ),
            pk=self.kwargs["pk"],
        )

        input_serializer = StaffInventoryUpdateSerializer(
            inventory,
            data=request.data,
            partial=partial,
            context=self.get_serializer_context(),
        )
        input_serializer.is_valid(raise_exception=True)

        inventory = input_serializer.save()

        output_serializer = StaffInventorySerializer(
            inventory,
            context=self.get_serializer_context(),
        )

        return Response(
            output_serializer.data,
            status=status.HTTP_200_OK,
        )


class StaffProductImageListCreateView(
    generics.ListCreateAPIView,
):
    permission_classes = [
        IsAuthenticated,
        IsActiveStaff,
    ]

    throttle_scope = "staff_catalog"
    serializer_class = StaffProductImageSerializer

    parser_classes = [
        MultiPartParser,
        FormParser,
        JSONParser,
    ]

    ordering = [
        "position",
        "created_at",
    ]

    def get_product(self):
        return get_object_or_404(
            Product,
            pk=self.kwargs["product_pk"],
        )

    def get_queryset(self):
        return ProductImage.objects.filter(
            product_id=self.kwargs["product_pk"],
        ).select_related(
            "product",
        )

    @transaction.atomic
    def create(self, request, *args, **kwargs):
        product = get_object_or_404(
            Product.objects.select_for_update(),
            pk=self.kwargs["product_pk"],
        )

        input_serializer = StaffProductImageSerializer(
            data=request.data,
            context=self.get_serializer_context(),
        )
        input_serializer.is_valid(raise_exception=True)

        existing_images = ProductImage.objects.filter(
            product=product,
        )

        is_first_image = not existing_images.exists()
        make_primary = is_first_image or input_serializer.validated_data.get(
            "is_primary",
            False,
        )

        if make_primary:
            existing_images.filter(
                is_primary=True,
            ).update(
                is_primary=False,
            )

        product_image = input_serializer.save(
            product=product,
            is_primary=make_primary,
        )

        output_serializer = StaffProductImageSerializer(
            product_image,
            context=self.get_serializer_context(),
        )

        return Response(
            output_serializer.data,
            status=status.HTTP_201_CREATED,
        )


class StaffProductImageDetailView(
    generics.RetrieveUpdateDestroyAPIView,
):
    permission_classes = [
        IsAuthenticated,
        IsActiveStaff,
    ]

    throttle_scope = "staff_catalog"
    serializer_class = StaffProductImageSerializer

    parser_classes = [
        MultiPartParser,
        FormParser,
        JSONParser,
    ]

    queryset = ProductImage.objects.select_related(
        "product",
    )

    @transaction.atomic
    def update(self, request, *args, **kwargs):
        partial = kwargs.pop(
            "partial",
            False,
        )

        product_image = get_object_or_404(
            ProductImage.objects.select_for_update().select_related(
                "product",
            ),
            pk=self.kwargs["pk"],
        )

        Product.objects.select_for_update().get(
            pk=product_image.product_id,
        )

        input_serializer = StaffProductImageSerializer(
            product_image,
            data=request.data,
            partial=partial,
            context=self.get_serializer_context(),
        )
        input_serializer.is_valid(raise_exception=True)

        requested_primary = input_serializer.validated_data.get(
            "is_primary",
        )

        if product_image.is_primary and requested_primary is False:
            raise serializers.ValidationError(
                {
                    "is_primary": (
                        "A primary image cannot be unset directly. "
                        "Set another image as primary instead."
                    )
                }
            )

        if requested_primary is True:
            ProductImage.objects.filter(
                product_id=product_image.product_id,
                is_primary=True,
            ).exclude(
                pk=product_image.pk,
            ).update(
                is_primary=False,
            )

        replacing_image = "image" in input_serializer.validated_data

        old_file_name = product_image.image.name
        old_storage = product_image.image.storage

        product_image = input_serializer.save()

        if (
            replacing_image
            and old_file_name
            and old_file_name != product_image.image.name
        ):
            transaction.on_commit(
                lambda: old_storage.delete(old_file_name),
                robust=True,
            )

        output_serializer = StaffProductImageSerializer(
            product_image,
            context=self.get_serializer_context(),
        )

        return Response(
            output_serializer.data,
            status=status.HTTP_200_OK,
        )

    @transaction.atomic
    def destroy(self, request, *args, **kwargs):
        product_image = get_object_or_404(
            ProductImage.objects.select_for_update().select_related(
                "product",
            ),
            pk=self.kwargs["pk"],
        )

        Product.objects.select_for_update().get(
            pk=product_image.product_id,
        )

        was_primary = product_image.is_primary
        file_name = product_image.image.name
        storage = product_image.image.storage

        replacement = (
            ProductImage.objects.select_for_update()
            .filter(
                product_id=product_image.product_id,
            )
            .exclude(
                pk=product_image.pk,
            )
            .order_by(
                "position",
                "created_at",
            )
            .first()
        )

        product_image.delete()

        if was_primary and replacement is not None:
            replacement.is_primary = True
            replacement.save(
                update_fields=[
                    "is_primary",
                ]
            )

        if file_name:
            transaction.on_commit(
                lambda: storage.delete(file_name),
                robust=True,
            )

        return Response(
            status=status.HTTP_204_NO_CONTENT,
        )


class StaffCategoryListCreateView(
    generics.ListCreateAPIView,
):
    permission_classes = [
        IsAuthenticated,
        IsActiveStaff,
    ]

    throttle_scope = "staff_catalog"
    serializer_class = StaffCategorySerializer

    queryset = Category.objects.all().order_by(
        "name",
    )

    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]

    filterset_fields = [
        "is_active",
    ]

    search_fields = [
        "name",
        "slug",
        "description",
    ]

    ordering_fields = [
        "name",
        "created_at",
        "updated_at",
    ]

    ordering = [
        "name",
    ]


class StaffCategoryDetailView(
    generics.RetrieveUpdateAPIView,
):
    permission_classes = [
        IsAuthenticated,
        IsActiveStaff,
    ]

    throttle_scope = "staff_catalog"
    serializer_class = StaffCategorySerializer

    queryset = Category.objects.all()


class StaffBrandListCreateView(
    generics.ListCreateAPIView,
):
    permission_classes = [
        IsAuthenticated,
        IsActiveStaff,
    ]

    throttle_scope = "staff_catalog"
    serializer_class = StaffBrandSerializer

    queryset = Brand.objects.all().order_by(
        "name",
    )

    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]

    filterset_fields = [
        "is_active",
    ]

    search_fields = [
        "name",
        "slug",
    ]

    ordering_fields = [
        "name",
        "id",
    ]

    ordering = [
        "name",
    ]


class StaffBrandDetailView(
    generics.RetrieveUpdateAPIView,
):
    permission_classes = [
        IsAuthenticated,
        IsActiveStaff,
    ]

    throttle_scope = "staff_catalog"
    serializer_class = StaffBrandSerializer

    queryset = Brand.objects.all()
