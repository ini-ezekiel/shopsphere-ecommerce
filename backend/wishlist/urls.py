from django.urls import path

from .views import (
    WishlistItemDeleteView,
    WishlistListCreateView,
)

app_name = "wishlist"


urlpatterns = [
    path(
        "wishlist/",
        WishlistListCreateView.as_view(),
        name="wishlist-list-create",
    ),
    path(
        "wishlist/items/<int:pk>/",
        WishlistItemDeleteView.as_view(),
        name="wishlist-item-delete",
    ),
]
