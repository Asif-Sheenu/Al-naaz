from rest_framework.permissions import BasePermission

from .services.access_service import get_accessible_branches
from users.permissions import IsAdmin


class CanAccessBranch(BasePermission):
    """
    Allows authenticated users to view branches they have access to.
    """

    message = "You do not have access to this branch."

    def has_permission(self, request, view):
        return request.user.is_authenticated

    def has_object_permission(self, request, view, obj):
        return (
            get_accessible_branches(request.user)
            .filter(pk=obj.pk)
            .exists()
        )


class CanManageBranches(BasePermission):
    """
    Only ADMIN users can create, update, delete,
    activate/deactivate, or manage users for branches.
    """

    message = "Only administrators can manage branches."

    def has_permission(self, request, view):
        return (
            request.user.is_authenticated
            and (
                request.user.is_superuser
                or request.user.role == "ADMIN"
            )
        )