from django_filters import rest_framework as filters

from .models import Product


class ProductFilter(filters.FilterSet):
    category = filters.CharFilter(
        field_name="category__slug",
        lookup_expr="iexact",
    )
    brand = filters.CharFilter(
        field_name="brand__slug",
        lookup_expr="iexact",
    )
    min_price = filters.NumberFilter(
        field_name="catalog_price",
        lookup_expr="gte",
    )
    max_price = filters.NumberFilter(
        field_name="catalog_price",
        lookup_expr="lte",
    )
    in_stock = filters.BooleanFilter(
        field_name="has_available_stock",
    )

    class Meta:
        model = Product
        fields = []
