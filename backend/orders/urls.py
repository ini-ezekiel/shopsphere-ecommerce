from django.urls import path

from .views import (
    CheckoutView,
    OrderCancelView,
    OrderDetailView,
    OrderListView,
)

app_name = "orders"


urlpatterns = [
    path("checkout/", CheckoutView.as_view(), name="checkout",),
    path("orders/", OrderListView.as_view(), name="order-list", ),
    path("orders/<str:order_number>/cancel/", OrderCancelView.as_view(), name="order-cancel",),
    path("orders/<str:order_number>/", OrderDetailView.as_view(), name="order-detail",),
]
