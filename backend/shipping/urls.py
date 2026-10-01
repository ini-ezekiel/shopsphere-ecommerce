from django.urls import path

from .views import (
    StaffOrderDetailView,
    StaffOrderListView,
    StaffOrderStatusUpdateView,
)

app_name = "shipping"

urlpatterns = [
    path(
        "staff/orders/",
        StaffOrderListView.as_view(),
        name="staff-order-list",
    ),
    path(
        "staff/orders/<str:order_number>/status/",
        StaffOrderStatusUpdateView.as_view(),
        name="staff-order-status-update",
    ),
    path(
        "staff/orders/<str:order_number>/",
        StaffOrderDetailView.as_view(),
        name="staff-order-detail",
    ),
]
