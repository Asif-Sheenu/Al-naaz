from rest_framework.permissions import BasePermission

from organization.services.user_branch_service import get_accessible_branches

from rest_framework.permissions import BasePermission

from organization.services.user_branch_service import get_accessible_branches

class CanAccessClearanceEmployee(BasePermission):
    """
    Users can access clearance records only for employees
    belonging to their accessible branches.
    """

    message = "You do not have access to this employee's branch."

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
        )

    def has_object_permission(self, request, view, obj):
        employee = getattr(obj, "employee", None)

        if employee is None:
            return False

        return get_accessible_branches(request.user).filter(
            pk=employee.branch_id
        ).exists()





class IsAdminManagerOrStaff(BasePermission):
    """
    Allow authenticated administrators, managers, and staff.
    """

    def has_permission(self, request, view):
        user = request.user

        return bool(
            user
            and user.is_authenticated
            and (
                user.is_superuser
                or user.role in ["ADMIN", "MANAGER", "STAFF"]
            )
        )


class CanAccessClearanceEmployee(BasePermission):
    message = "You do not have access to this employee's branch."

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
        )

    def has_object_permission(self, request, view, obj):
        employee = getattr(obj, "employee", None)

        if employee is None:
            return False

        return get_accessible_branches(
            request.user
        ).filter(
            pk=employee.branch_id
        ).exists()    