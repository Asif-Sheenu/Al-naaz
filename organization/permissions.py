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


from rest_framework.permissions import BasePermission

from .services.user_branch_service import get_accessible_branches


class CanAccessDepartment(BasePermission):

    message = "You do not have access to this department."

    def has_permission(self, request, view):

        user = request.user

        if not user or not user.is_authenticated:
            return False

        if user.is_superuser or user.role == "ADMIN":
            return True

        if user.role in ["MANAGER", "STAFF"]:
            return True

        return False

    def has_object_permission(self, request, view, obj):

        user = request.user

        if user.is_superuser or user.role == "ADMIN":
            return True

        accessible_branch_ids = (
            get_accessible_branches(user)
            .values_list("id", flat=True)
        )

        return obj.branch_id in accessible_branch_ids


class CanManageDepartments(BasePermission):

    message = "You do not have permission to manage departments."

    def has_permission(self, request, view):

        user = request.user

        if not user or not user.is_authenticated:
            return False

        if user.is_superuser or user.role == "ADMIN":
            return True

        if user.role == "MANAGER":
            return True

        return False

    def has_object_permission(self, request, view, obj):

        user = request.user

        if user.is_superuser or user.role == "ADMIN":
            return True

        if user.role == "MANAGER":

            accessible_branch_ids = (
                get_accessible_branches(user)
                .values_list("id", flat=True)
            )

            return obj.branch_id in accessible_branch_ids

        return False    