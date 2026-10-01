import logging

from django.conf import settings
from django.core.mail import send_mail
from django.db import transaction

from .models import Notification

logger = logging.getLogger(__name__)


class NotificationError(Exception):
    def __init__(self, message):
        self.message = message
        super().__init__(message)


def _send_notification_email(
    *,
    recipient_email,
    subject,
    message,
    link="",
):
    if not getattr(
        settings,
        "NOTIFICATION_EMAILS_ENABLED",
        True,
    ):
        return

    recipient_email = str(recipient_email or "").strip()
    subject = str(subject or "").strip()
    message = str(message or "").strip()
    link = str(link or "").strip()

    if not recipient_email or not subject or not message:
        return

    if link:
        frontend_url = settings.FRONTEND_URL.rstrip("/")
        notification_url = f"{frontend_url}{link}"

        message = f"{message}\n\n" "View the update here:\n" f"{notification_url}"

    try:
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[recipient_email],
            fail_silently=False,
        )
    except Exception:
        logger.exception(
            "Unable to send notification email to %s.",
            recipient_email,
        )


def create_notification(
    *,
    user,
    event_type,
    title,
    message,
    deduplication_key,
    link="",
    metadata=None,
    email_subject="",
):
    if user is None or user.pk is None:
        raise NotificationError("A saved user is required for a notification.")

    event_type = str(event_type or "").strip()
    title = str(title or "").strip()
    message = str(message or "").strip()
    deduplication_key = str(deduplication_key or "").strip()
    link = str(link or "").strip()
    email_subject = str(email_subject or "").strip()

    valid_event_types = {choice.value for choice in Notification.EventType}

    if event_type not in valid_event_types:
        raise NotificationError("The notification event type is invalid.")

    if not title:
        raise NotificationError("A notification title is required.")

    if len(title) > 150:
        raise NotificationError(
            "The notification title cannot exceed " "150 characters."
        )

    if not message:
        raise NotificationError("A notification message is required.")

    if not deduplication_key:
        raise NotificationError("A notification deduplication key is required.")

    if len(deduplication_key) > 255:
        raise NotificationError(
            "The notification deduplication key cannot " "exceed 255 characters."
        )

    if len(link) > 500:
        raise NotificationError(
            "The notification link cannot exceed " "500 characters."
        )

    if metadata is None:
        metadata = {}

    if not isinstance(metadata, dict):
        raise NotificationError("Notification metadata must be an object.")

    notification, created = Notification.objects.get_or_create(
        deduplication_key=deduplication_key,
        defaults={
            "user": user,
            "event_type": event_type,
            "title": title,
            "message": message,
            "link": link,
            "metadata": metadata,
        },
    )

    if created and email_subject and user.email:
        transaction.on_commit(
            lambda: _send_notification_email(
                recipient_email=user.email,
                subject=email_subject,
                message=message,
                link=link,
            ),
            robust=True,
        )

    return notification, created
