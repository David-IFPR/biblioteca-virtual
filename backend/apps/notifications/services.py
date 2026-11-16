from django.utils import timezone

from apps.accounts.models import User
from apps.notifications.models import Notification


def notify_user(user, kind, title, message):
    if user is None or not user.is_active:
        return None
    return Notification.objects.create(
        recipient=user, kind=kind, title=title, message=message
    )


def notify_admins(kind, title, message):
    admins = User.objects.filter(role=User.Role.ADMIN, is_active=True)
    Notification.objects.bulk_create(
        [
            Notification(recipient=admin, kind=kind, title=title, message=message)
            for admin in admins
        ]
    )


def mark_read(notification):
    if not notification.is_read:
        notification.is_read = True
        notification.read_at = timezone.now()
        notification.save(update_fields=["is_read", "read_at"])
    return notification
