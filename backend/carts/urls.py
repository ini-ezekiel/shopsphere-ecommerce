from django.urls import path

from .views import (
    CartClearView,
    CartDetailView,
    CartItemCreateView,
    CartItemDetailView,
)

urlpatterns = [
    path("cart/", CartDetailView.as_view(), name="cart-detail",),
    path("cart/items/", CartItemCreateView.as_view(), name="cart-item-create",),
    path("cart/items/<int:pk>/", CartItemDetailView.as_view(), name="cart-item-detail",),
    path("cart/clear/", CartClearView.as_view(), name="cart-clear",),
]
