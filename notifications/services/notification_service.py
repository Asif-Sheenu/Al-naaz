from django.contrib.auth import get_user_model

from ..models import Notification


User = get_user_model()


def notify_admins(
    *,
    notification_type,
    title,
    message,
    module,
    object_id=None,
):
    admins = User.objects.filter(
        role="ADMIN",
        is_active=True,
    )

    notifications = [
        Notification(
            recipient=admin,
            notification_type=notification_type,
            title=title,
            message=message,
            module=module,
            object_id=object_id,
        )
        for admin in admins
    ]

    if notifications:
        Notification.objects.bulk_create(
            notifications
        )

    return notifications