from django.db.models import QuerySet

from ..models import Branch


def get_accessible_branches(user) -> QuerySet:
    """
    Return the active branches accessible to the authenticated user.

    ADMIN/superusers:
        Company-wide branch access.

    MANAGER/STAFF:
        Only explicitly assigned active branches.
    """

    if not user.is_authenticated:
        return Branch.objects.none()

    if user.is_superuser or user.role == "ADMIN":
        return (
            Branch.objects
            .filter(is_active=True)
            .select_related("company")
            .order_by("name")
        )

    return (
        user.branches
        .filter(is_active=True)
        .select_related("company")
        .order_by("name")
    )