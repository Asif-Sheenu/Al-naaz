from django.db import transaction
from django.db.models import QuerySet

from ..models import Branch
from users.models import User


@transaction.atomic
def assign_user_to_branch(*, branch, user):
    if not branch.is_active:
        raise ValueError(
            "Cannot assign a user to an inactive branch."
        )

    if not user.is_active:
        raise ValueError(
            "Cannot assign an inactive user to a branch."
        )

    branch.users.add(user)

    return branch


@transaction.atomic
def remove_user_from_branch(*, branch, user):
    branch.users.remove(user)

    return branch


def get_accessible_branches(user) -> QuerySet:

    if not user.is_authenticated:
        return Branch.objects.none()

    if user.is_superuser or user.role == "ADMIN":
        return (
            Branch.objects
            .filter(is_active=True)
            .select_related("company")
        )

    return (
        user.branches
        .filter(is_active=True)
        .select_related("company")
    )