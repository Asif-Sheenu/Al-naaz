from rest_framework.permissions import BasePermission

class IsAdmin(BasePermission):

    def has_permission(self, request, view):

        return (
            request.user.is_authenticated
            and (
                request.user.role == "ADMIN"
                or request.user.is_superuser
            )
        )

class IsStaff(BasePermission):
    def has_permission(self, request, view):
        return (
            request.user.is_authenticated
            and request.user.role == "STAFF"
        )


class IsAdminOrStaff(BasePermission):

    def has_permission(self, request, view):

        return (
            request.user.is_authenticated and
            (
                request.user.is_superuser or
                request.user.role in ["ADMIN", "STAFF"]
            )
        )        