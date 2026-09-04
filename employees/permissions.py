from rest_framework.permissions import BasePermission

from organization.services.access_service import (
    get_accessible_branches,
)


class CanManageEmployees(BasePermission):

    message = "You do not have permission to manage employees."

    def has_permission(self, request, view):

        user = request.user

        if not user.is_authenticated:
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

        return (
            get_accessible_branches(user)
            .filter(
                pk=obj.branch_id
            )
            .exists()
        )



class CanManageEmployeeSalary(BasePermission):

    message = "You do not have permission to manage employee salary."

    def has_permission(self, request, view):

        user = request.user

        if not user.is_authenticated:
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

            return (
                get_accessible_branches(user)
                .filter(
                    pk=obj.branch_id
                )
                .exists()
            )

        return False    