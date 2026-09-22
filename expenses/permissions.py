from rest_framework.permissions import BasePermission

from organization.services.access_service import (
    get_accessible_branches,
)


class FinanceBranchPermission(BasePermission):
    """
    Base permission for finance operations.

    ADMIN:
        All branches.

    MANAGER:
        Accessible branches only.

    STAFF:
        Accessible branches only.
    """

    def has_branch_access(self, user, branch):
        if user.is_superuser or user.role == "ADMIN":
            return True

        return get_accessible_branches(user).filter(
            pk=branch.pk
        ).exists()


class CanViewFinance(FinanceBranchPermission):
    message = "You do not have permission to view this financial information."

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
        )


class CanCreateExpense(FinanceBranchPermission):
    message = "You do not have permission to create expenses."

    def has_permission(self, request, view):
        user = request.user

        if not user or not user.is_authenticated:
            return False

        return user.role in {
            "STAFF",
            "MANAGER",
            "ADMIN",
        } or user.is_superuser


class CanCreateDailySales(FinanceBranchPermission):
    message = "You do not have permission to create daily sales."

    def has_permission(self, request, view):
        user = request.user

        if not user or not user.is_authenticated:
            return False

        return user.role in {
            "STAFF",
            "MANAGER",
            "ADMIN",
        } or user.is_superuser


class CanPostDailySales(FinanceBranchPermission):
    message = "Only managers or administrators can post daily sales."

    def has_permission(self, request, view):
        user = request.user

        if not user or not user.is_authenticated:
            return False

        return user.role in {
            "MANAGER",
            "ADMIN",
        } or user.is_superuser


class CanManageFinancialAccounts(FinanceBranchPermission):
    message = "Only administrators can manage financial accounts."

    def has_permission(self, request, view):
        user = request.user

        if not user or not user.is_authenticated:
            return False

        return user.role == "ADMIN" or user.is_superuser


class CanTransferMoney(FinanceBranchPermission):
    message = "Only managers or administrators can transfer money."

    def has_permission(self, request, view):
        user = request.user

        if not user or not user.is_authenticated:
            return False

        return user.role in {
            "MANAGER",
            "ADMIN",
        } or user.is_superuser


class CanSettleReceivable(FinanceBranchPermission):
    message = "Only managers or administrators can settle receivables."

    def has_permission(self, request, view):
        user = request.user

        if not user or not user.is_authenticated:
            return False

        return user.role in {
            "MANAGER",
            "ADMIN",
        } or user.is_superuser


class CanManageDeliveryPartners(FinanceBranchPermission):
    message = "Only administrators can manage delivery partner configuration."

    def has_permission(self, request, view):
        user = request.user

        if not user or not user.is_authenticated:
            return False

        return user.role == "ADMIN" or user.is_superuser    

    

class CanApproveExpenseAdjustment(FinanceBranchPermission):
    message = (
        "Only managers or administrators can approve "
        "expense adjustments."
    )

    def has_permission(self, request, view):
        user = request.user

        if not user or not user.is_authenticated:
            return False

        return user.role in {
            "MANAGER",
            "ADMIN",
        } or user.is_superuser    