
from django.contrib.auth import get_user_model

from ..models import Notification


User = get_user_model()


def _create_notifications(
    *,
    recipients,
    notification_type,
    title,
    message,
    module,
    object_id=None,
):
    """Create one notification per active, unique recipient."""

    notifications = []
    seen_user_ids = set()

    for user in recipients:
        if not user.is_active or user.pk in seen_user_ids:
            continue

        seen_user_ids.add(user.pk)

        notifications.append(
            Notification(
                recipient=user,
                notification_type=notification_type,
                title=title,
                message=message,
                module=module,
                object_id=object_id,
            )
        )

    if notifications:
        Notification.objects.bulk_create(notifications)

    return notifications


def notify_admins_and_managers(
    *,
    notification_type,
    title,
    message,
    module,
    object_id=None,
    branch=None,
):
    """
    Notify active Admins and Managers.

    Admins receive notifications across branches.
    When a branch is supplied, Managers must be assigned
    to that branch.
    """

    admins = User.objects.filter(
        role="ADMIN",
        is_active=True,
    )

    managers = User.objects.filter(
        role="MANAGER",
        is_active=True,
    )

    if branch is not None:
        managers = managers.filter(
            branches=branch,
        )

    recipients = list(admins) + list(managers)

    return _create_notifications(
        recipients=recipients,
        notification_type=notification_type,
        title=title,
        message=message,
        module=module,
        object_id=object_id,
    )


def notify_user(
    *,
    user,
    notification_type,
    title,
    message,
    module,
    object_id=None,
):
    """Notify one specific active user."""

    if user is None or not user.is_active:
        return None

    return Notification.objects.create(
        recipient=user,
        notification_type=notification_type,
        title=title,
        message=message,
        module=module,
        object_id=object_id,
    )
