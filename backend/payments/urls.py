from django.urls import path

from .views import (
    CustomerRefundDetailView,
    CustomerRefundListView,
    PaymentInitializeView,
    PaymentVerifyView,
    PaystackWebhookView,
    StaffRefundInitiateView,
    StaffRefundListView,
)

app_name = "payments"


urlpatterns = [
    path(
        "orders/<str:order_number>/payments/initialize/",
        PaymentInitializeView.as_view(),
        name="payment-initialize",
    ),
    path(
        "payments/<str:reference>/verify/",
        PaymentVerifyView.as_view(),
        name="payment-verify",
    ),
    path(
        "staff/payments/<str:reference>/refund/",
        StaffRefundInitiateView.as_view(),
        name="staff-refund-initiate",
    ),
    path(
        "staff/refunds/",
        StaffRefundListView.as_view(),
        name="staff-refund-list",
    ),
    path(
        "refunds/me/",
        CustomerRefundListView.as_view(),
        name="customer-refund-list",
    ),
    path(
        "refunds/<str:reference>/",
        CustomerRefundDetailView.as_view(),
        name="customer-refund-detail",
    ),
    path(
        "payments/paystack/webhook/",
        PaystackWebhookView.as_view(),
        name="paystack-webhook",
    ),
]
