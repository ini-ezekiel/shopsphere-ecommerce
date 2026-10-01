from django.urls import path

from .views import (
    CustomerReviewDetailView,
    CustomerReviewListView,
    ProductReviewListCreateView,
    StaffReviewDetailView,
    StaffReviewListView,
)

app_name = "reviews"

urlpatterns = [
    path(
        "catalog/products/<slug:product_slug>/reviews/",
        ProductReviewListCreateView.as_view(),
        name="product-review-list-create",
    ),
    path(
        "reviews/me/",
        CustomerReviewListView.as_view(),
        name="customer-review-list",
    ),
    path(
        "reviews/<int:pk>/",
        CustomerReviewDetailView.as_view(),
        name="customer-review-detail",
    ),
    path(
        "staff/reviews/",
        StaffReviewListView.as_view(),
        name="staff-review-list",
    ),
    path(
        "staff/reviews/<int:pk>/",
        StaffReviewDetailView.as_view(),
        name="staff-review-detail",
    ),
]
