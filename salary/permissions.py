from rest_framework.permissions import BasePermission

from organization.services.access_service import (
    get_accessible_branches,
)


class CanManageSalary(BasePermission):

    message = "You do not have permission to manage salary."

    def has_permission(self, request, view):

        user = request.user

        if not user or not user.is_authenticated:
            return False

        # Admin can manage salary
        if user.is_superuser or user.role == "ADMIN":
            return True

        # Manager can manage salary
        if user.role == "MANAGER":
            return True

        # Staff cannot manage salary
        return False

    def has_object_permission(self, request, view, obj):

        user = request.user

        # Admin can access everything
        if user.is_superuser or user.role == "ADMIN":
            return True

        # Manager can access salary
        # only if employee belongs to an accessible branch
        if user.role == "MANAGER":

            accessible_branch_ids = (
                get_accessible_branches(user)
                .values_list(
                    "id",
                    flat=True,
                )
            )

            return (
                obj.employee.branch_id
                in accessible_branch_ids
            )

        return False