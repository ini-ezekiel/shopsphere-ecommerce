from django.urls import path

from .views import (
    CustomerNotificationListView,
    CustomerNotificationMarkAllReadView,
    CustomerNotificationMarkReadView,
    CustomerNotificationUnreadCountView,
)

app_name = "notifications"


urlpatterns = [
    path(
        "notifications/",
        CustomerNotificationListView.as_view(),
        name="customer-notification-list",
    ),
    path(
        "notifications/unread-count/",
        CustomerNotificationUnreadCountView.as_view(),
        name="customer-notification-unread-count",
    ),
    path(
        "notifications/<int:pk>/read/",
        CustomerNotificationMarkReadView.as_view(),
        name="customer-notification-mark-read",
    ),
    path(
        "notifications/read-all/",
        CustomerNotificationMarkAllReadView.as_view(),
        name="customer-notification-mark-all-read",
    ),
]
