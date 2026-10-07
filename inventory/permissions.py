from rest_framework.permissions import BasePermission


class CanViewInventory(BasePermission):
    message = "You do not have permission to view inventory."

    def has_permission(self, request, view):
        return (
            request.user.is_authenticated
            and request.user.role in ["STAFF", "MANAGER", "ADMIN"]
        )


class CanCreatePurchase(BasePermission):
    message = "You do not have permission to create purchases."

    def has_permission(self, request, view):
        return (
            request.user.is_authenticated
            and request.user.role in ["STAFF", "MANAGER", "ADMIN"]
        )


class CanCreateStockUsage(BasePermission):
    message = "You do not have permission to record stock usage."

    def has_permission(self, request, view):
        return (
            request.user.is_authenticated
            and request.user.role in ["STAFF", "MANAGER", "ADMIN"]
        )


class CanAdjustStock(BasePermission):
    message = "You do not have permission to adjust stock."

    def has_permission(self, request, view):
        return (
            request.user.is_authenticated
            and request.user.role in ["STAFF", "MANAGER", "ADMIN"]
        )