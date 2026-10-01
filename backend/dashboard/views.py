from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .permissions import IsActiveStaff
from .serializers import (
    DashboardPeriodQuerySerializer,
    DashboardSummarySerializer,
)
from .services import build_dashboard_summary


class DashboardSummaryView(APIView):
    permission_classes = [
        IsAuthenticated,
        IsActiveStaff,
    ]

    throttle_scope = "dashboard_read"

    def get(self, request):
        query_serializer = DashboardPeriodQuerySerializer(
            data=request.query_params,
        )
        query_serializer.is_valid(
            raise_exception=True,
        )

        period = query_serializer.validated_data["period"]

        summary = build_dashboard_summary(
            period=period,
        )

        output_serializer = DashboardSummarySerializer(
            summary,
        )

        return Response(
            output_serializer.data,
            status=status.HTTP_200_OK,
        )
