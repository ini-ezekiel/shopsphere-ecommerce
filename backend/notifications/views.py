from django.shortcuts import get_object_or_404
from django.utils import timezone

from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Notification
from .serializers import NotificationSerializer


class CustomerNotificationListView(
    generics.ListAPIView,
):
    permission_classes = [
        IsAuthenticated,
    ]

    serializer_class = NotificationSerializer
    throttle_scope = "notification_read"

    def get_queryset(self):
        queryset = Notification.objects.filter(
            user=self.request.user,
        )

        unread_only = (
            self.request.query_params.get(
                "unread",
                "",
            )
            .strip()
            .lower()
        )

        if unread_only in {
            "1",
            "true",
            "yes",
        }:
            queryset = queryset.filter(
                read_at__isnull=True,
            )

        return queryset


class CustomerNotificationUnreadCountView(
    APIView,
):
    permission_classes = [
        IsAuthenticated,
    ]

    throttle_scope = "notification_read"

    def get(self, request):
        unread_count = Notification.objects.filter(
            user=request.user,
            read_at__isnull=True,
        ).count()

        return Response(
            {
                "unread_count": unread_count,
            },
            status=status.HTTP_200_OK,
        )


class CustomerNotificationMarkReadView(
    APIView,
):
    permission_classes = [
        IsAuthenticated,
    ]

    throttle_scope = "notification_write"

    def patch(
        self,
        request,
        pk,
    ):
        notification = get_object_or_404(
            Notification,
            pk=pk,
            user=request.user,
        )

        marked_read = False

        if notification.read_at is None:
            notification.read_at = timezone.now()

            notification.save(
                update_fields=[
                    "read_at",
                ]
            )

            marked_read = True

        serializer = NotificationSerializer(
            notification,
            context={
                "request": request,
            },
        )

        response_data = dict(serializer.data)
        response_data["marked_read"] = marked_read

        return Response(
            response_data,
            status=status.HTTP_200_OK,
        )


class CustomerNotificationMarkAllReadView(
    APIView,
):
    permission_classes = [
        IsAuthenticated,
    ]

    throttle_scope = "notification_write"

    def post(self, request):
        marked_read_count = Notification.objects.filter(
            user=request.user,
            read_at__isnull=True,
        ).update(
            read_at=timezone.now(),
        )

        return Response(
            {
                "marked_read_count": (marked_read_count),
            },
            status=status.HTTP_200_OK,
        )
