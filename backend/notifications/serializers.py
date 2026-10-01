from rest_framework import serializers

from .models import Notification


class NotificationSerializer(serializers.ModelSerializer):
    event_type_display = serializers.CharField(
        source="get_event_type_display",
        read_only=True,
    )

    is_read = serializers.BooleanField(
        read_only=True,
    )

    class Meta:
        model = Notification

        fields = [
            "id",
            "event_type",
            "event_type_display",
            "title",
            "message",
            "link",
            "metadata",
            "is_read",
            "read_at",
            "created_at",
        ]

        read_only_fields = fields
