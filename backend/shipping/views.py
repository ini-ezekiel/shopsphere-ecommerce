from django.db.models import Q
from rest_framework import generics, status
from rest_framework.exceptions import ValidationError
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from orders.models import Order

from .permissions import IsActiveStaff
from .serializers import (
    FulfillmentOrderSerializer,
    FulfillmentTransitionSerializer,
    StaffOrderListSerializer,
)
from .services import (
    FulfillmentError,
    transition_order_status,
)


class StaffOrderPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 100


class StaffOrderListView(generics.ListAPIView):
    permission_classes = [
        IsAuthenticated,
        IsActiveStaff,
    ]

    serializer_class = StaffOrderListSerializer
    pagination_class = StaffOrderPagination

    def get_queryset(self):
        queryset = Order.objects.select_related(
            "user",
            "shipment",
        ).order_by("-created_at")

        order_status = self.request.query_params.get(
            "status",
            "",
        ).strip()

        inventory_status = self.request.query_params.get(
            "inventory_status",
            "",
        ).strip()

        search = self.request.query_params.get(
            "search",
            "",
        ).strip()

        ordering = self.request.query_params.get(
            "ordering",
            "-created_at",
        ).strip()

        if order_status:
            if order_status not in Order.Status.values:
                raise ValidationError({"status": ("Enter a valid order status.")})

            queryset = queryset.filter(
                status=order_status,
            )

        if inventory_status:
            if inventory_status not in Order.InventoryStatus.values:
                raise ValidationError(
                    {"inventory_status": ("Enter a valid inventory status.")}
                )

            queryset = queryset.filter(
                inventory_status=inventory_status,
            )

        if search:
            queryset = queryset.filter(
                Q(order_number__icontains=search)
                | Q(user__email__icontains=search)
                | Q(recipient_name__icontains=search)
                | Q(phone_number__icontains=search)
                | Q(shipment__tracking_number__icontains=search)
            )

        allowed_ordering = {
            "created_at",
            "-created_at",
            "updated_at",
            "-updated_at",
            "total_amount",
            "-total_amount",
        }

        if ordering not in allowed_ordering:
            raise ValidationError({"ordering": ("Enter a valid ordering value.")})

        return queryset.order_by(ordering)


class StaffOrderDetailView(generics.RetrieveAPIView):
    permission_classes = [
        IsAuthenticated,
        IsActiveStaff,
    ]

    serializer_class = FulfillmentOrderSerializer
    lookup_field = "order_number"
    lookup_url_kwarg = "order_number"

    queryset = (
        Order.objects.select_related(
            "user",
            "shipment",
        )
        .prefetch_related(
            "items",
            "status_history",
            "payments",
            "payments__refund",
        )
        .all()
    )


class StaffOrderStatusUpdateView(APIView):
    permission_classes = [
        IsAuthenticated,
        IsActiveStaff,
    ]

    def patch(
        self,
        request,
        order_number,
    ):
        serializer = FulfillmentTransitionSerializer(
            data=request.data,
        )
        serializer.is_valid(raise_exception=True)

        try:
            order, shipment, transitioned = transition_order_status(
                order_number=order_number,
                new_status=serializer.validated_data["status"],
                changed_by=request.user,
                note=serializer.validated_data["note"],
                carrier=serializer.validated_data["carrier"],
                tracking_number=(serializer.validated_data["tracking_number"]),
            )
        except FulfillmentError as error:
            return Response(
                {
                    "detail": error.message,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        output_serializer = FulfillmentOrderSerializer(
            order,
            context={
                "request": request,
            },
        )

        response_data = dict(output_serializer.data)
        response_data["transitioned"] = transitioned

        return Response(
            response_data,
            status=status.HTTP_200_OK,
        )
