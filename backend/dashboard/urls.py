from django.urls import path

from .views import DashboardSummaryView

app_name = "dashboard"

urlpatterns = [
    path(
        "staff/dashboard/summary/",
        DashboardSummaryView.as_view(),
        name="staff-dashboard-summary",
    ),
]
