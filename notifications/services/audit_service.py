from ..models import ActivityLog


def log_activity(
    *,
    user,
    action,
    module,
    description,
    object_id=None,
    old_data=None,
    new_data=None,
):
    return ActivityLog.objects.create(
        user=user,
        action=action,
        module=module,
        object_id=object_id,
        description=description,
        old_data=old_data,
        new_data=new_data,
    )