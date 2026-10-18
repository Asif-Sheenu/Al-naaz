import logging

from django.db import transaction
from django.utils import timezone

from expenses.models import (
    Expense,
    ExpenseAdjustment,
    FinancialTransaction,
)

from expenses.services.financial_transaction_service import (
    create_financial_transaction,
)

from notifications.services.notification_service import (
    notify_admins_and_managers,
    notify_user,
)

logger = logging.getLogger(__name__)


def _notify_adjustment_requested(
    *,
    branch,
    adjustment_id,
    expense_id,
    requested_by,
    old_amount,
    new_amount,
    reason,
):
    try:
        notify_admins_and_managers(
            notification_type="APPROVAL",
            title="Expense Adjustment Requested",
            message=(
                f"Adjustment #{adjustment_id} requested for "
                f"Expense #{expense_id}. "
                f"Previous amount: ₹{old_amount}. "
                f"Requested amount: ₹{new_amount}. "
                f"Requested by: {requested_by}. "
                f"Reason: {reason}"
            ),
            module="FINANCE",
            object_id=adjustment_id,
            branch=branch,
        )
    except Exception:
        logger.exception(
            "Failed to notify admins about expense adjustment %s",
            adjustment_id,
        )


def _notify_adjustment_approved(
    *,
    requester,
    adjustment_id,
    expense_id,
    new_amount,
):
    try:
        notify_user(
            user=requester,
            notification_type="INFO",
            title="Expense Adjustment Approved",
            message=(
                f"Your adjustment request #{adjustment_id} for "
                f"Expense #{expense_id} has been approved. "
                f"The updated expense amount is ₹{new_amount}."
            ),
            module="FINANCE",
            object_id=adjustment_id,
        )
    except Exception:
        logger.exception(
            "Failed to notify requester about approved adjustment %s",
            adjustment_id,
        )


def _notify_adjustment_rejected(
    *,
    requester,
    adjustment_id,
    expense_id,
    rejection_reason,
):
    try:
        notify_user(
            user=requester,
            notification_type="WARNING",
            title="Expense Adjustment Rejected",
            message=(
                f"Your adjustment request #{adjustment_id} for "
                f"Expense #{expense_id} has been rejected. "
                f"Reason: {rejection_reason}"
            ),
            module="FINANCE",
            object_id=adjustment_id,
        )
    except Exception:
        logger.exception(
            "Failed to notify requester about rejected adjustment %s",
            adjustment_id,
        )


@transaction.atomic
def request_expense_adjustment(
    *,
    expense,
    new_amount,
    new_payment_account,
    new_expense_date,
    new_category,
    new_description,
    reason,
    requested_by,
):
    # 1. Validate expense
    if not expense:
        raise ValueError("Expense does not exist.")

    # 2. Validate new amount
    if new_amount <= 0:
        raise ValueError(
            "New expense amount must be greater than zero."
        )

    # 3. Validate payment account
    if not new_payment_account.is_active:
        raise ValueError(
            "The new payment account is inactive."
        )

    if new_payment_account.branch_id != expense.branch_id:
        raise ValueError(
            "Payment account must belong to the same branch "
            "as the expense."
        )

    # 4. Validate category
    if not new_category.is_active:
        raise ValueError(
            "The new expense category is inactive."
        )

    # 5. Validate reason
    if not reason or not reason.strip():
        raise ValueError(
            "A reason is required for an expense adjustment."
        )

    # 6. Prevent multiple pending adjustments
    pending_exists = ExpenseAdjustment.objects.filter(
        expense=expense,
        status=ExpenseAdjustment.Status.PENDING,
    ).exists()

    if pending_exists:
        raise ValueError(
            "This expense already has a pending adjustment."
        )

    # 7. Create adjustment request
    adjustment = ExpenseAdjustment.objects.create(
        expense=expense,
        requested_by=requested_by,
        status=ExpenseAdjustment.Status.PENDING,

        # Original values
        old_amount=expense.amount,
        old_payment_account=expense.payment_account,
        old_expense_date=expense.expense_date,
        old_category=expense.category,
        old_description=expense.description,

        # Requested values
        new_amount=new_amount,
        new_payment_account=new_payment_account,
        new_expense_date=new_expense_date,
        new_category=new_category,
        new_description=new_description,
        reason=reason.strip(),
    )

    # 8. Notify admins/managers after successful commit
    transaction.on_commit(
        lambda: _notify_adjustment_requested(
            branch=expense.branch,
            adjustment_id=adjustment.id,
            expense_id=expense.id,
            requested_by=str(requested_by),
            old_amount=adjustment.old_amount,
            new_amount=adjustment.new_amount,
            reason=adjustment.reason,
        )
    )

    return adjustment


@transaction.atomic
def approve_expense_adjustment(
    *,
    adjustment,
    approved_by,
):
    # 1. Lock adjustment
    locked_adjustment = (
        ExpenseAdjustment.objects
        .select_for_update()
        .get(pk=adjustment.pk)
    )

    # 2. Lock expense
    expense = (
        Expense.objects
        .select_for_update()
        .get(pk=locked_adjustment.expense_id)
    )

    # 3. Validate status
    if locked_adjustment.status != ExpenseAdjustment.Status.PENDING:
        raise ValueError(
            "Only pending expense adjustments can be approved."
        )

    # 4. Ensure expense has not changed
    if (
        expense.amount != locked_adjustment.old_amount
        or expense.payment_account_id
        != locked_adjustment.old_payment_account_id
        or expense.expense_date
        != locked_adjustment.old_expense_date
        or expense.category_id
        != locked_adjustment.old_category_id
        or expense.description
        != locked_adjustment.old_description
    ):
        raise ValueError(
            "This expense has changed since the adjustment was "
            "requested. Create a new adjustment request."
        )

    # 5. Validate new account
    new_account = locked_adjustment.new_payment_account

    if not new_account.is_active:
        raise ValueError(
            "Cannot approve adjustment using an inactive "
            "financial account."
        )

    if new_account.branch_id != expense.branch_id:
        raise ValueError(
            "New payment account does not belong to the expense branch."
        )

    # 6. Validate new category
    new_category = locked_adjustment.new_category

    if not new_category.is_active:
        raise ValueError(
            "Cannot approve adjustment using an inactive "
            "expense category."
        )

    # 7. Verify original financial transaction exists
    original_transaction_exists = (
        FinancialTransaction.objects.filter(
            branch_id=expense.branch_id,
            transaction_type=(
                FinancialTransaction.TransactionType.EXPENSE
            ),
            direction=FinancialTransaction.Direction.OUT,
            reference=f"EXPENSE-{expense.id}",
        ).exists()
    )

    if not original_transaction_exists:
        raise ValueError(
            "Original financial transaction for this expense "
            "was not found."
        )

    old_account = locked_adjustment.old_payment_account
    old_amount = locked_adjustment.old_amount
    old_date = locked_adjustment.old_expense_date

    new_amount = locked_adjustment.new_amount
    new_date = locked_adjustment.new_expense_date

    # 8. Apply financial correction
    if (
        old_account.id == new_account.id
        and old_date == new_date
    ):
        # Same account and date: record only the difference.
        amount_difference = new_amount - old_amount

        if amount_difference > 0:
            create_financial_transaction(
                branch=expense.branch,
                account=old_account,
                transaction_type=(
                    FinancialTransaction.TransactionType.ADJUSTMENT
                ),
                direction=FinancialTransaction.Direction.OUT,
                amount=amount_difference,
                transaction_date=new_date,
                created_by=approved_by,
                description=(
                    f"Expense #{expense.id} adjustment: "
                    f"increased from {old_amount} to {new_amount}. "
                    f"Reason: {locked_adjustment.reason}"
                ),
                reference=(
                    f"EXPENSE-{expense.id}-"
                    f"ADJUSTMENT-{locked_adjustment.id}"
                ),
            )

        elif amount_difference < 0:
            create_financial_transaction(
                branch=expense.branch,
                account=old_account,
                transaction_type=(
                    FinancialTransaction.TransactionType.ADJUSTMENT
                ),
                direction=FinancialTransaction.Direction.IN,
                amount=abs(amount_difference),
                transaction_date=new_date,
                created_by=approved_by,
                description=(
                    f"Expense #{expense.id} adjustment: "
                    f"decreased from {old_amount} to {new_amount}. "
                    f"Reason: {locked_adjustment.reason}"
                ),
                reference=(
                    f"EXPENSE-{expense.id}-"
                    f"ADJUSTMENT-{locked_adjustment.id}"
                ),
            )

    else:
        # Different account or date: reverse old effect and
        # record the new effect.
        create_financial_transaction(
            branch=expense.branch,
            account=old_account,
            transaction_type=(
                FinancialTransaction.TransactionType.ADJUSTMENT
            ),
            direction=FinancialTransaction.Direction.IN,
            amount=old_amount,
            transaction_date=old_date,
            created_by=approved_by,
            description=(
                f"Reverse old financial effect for Expense #{expense.id}. "
                f"Adjustment #{locked_adjustment.id}. "
                f"Reason: {locked_adjustment.reason}"
            ),
            reference=(
                f"EXPENSE-{expense.id}-"
                f"ADJUSTMENT-{locked_adjustment.id}-REVERSE"
            ),
        )

        create_financial_transaction(
            branch=expense.branch,
            account=new_account,
            transaction_type=(
                FinancialTransaction.TransactionType.ADJUSTMENT
            ),
            direction=FinancialTransaction.Direction.OUT,
            amount=new_amount,
            transaction_date=new_date,
            created_by=approved_by,
            description=(
                f"Apply new financial effect for Expense #{expense.id}. "
                f"Adjustment #{locked_adjustment.id}. "
                f"Reason: {locked_adjustment.reason}"
            ),
            reference=(
                f"EXPENSE-{expense.id}-"
                f"ADJUSTMENT-{locked_adjustment.id}-APPLY"
            ),
        )

    # 9. Update actual expense
    expense.amount = new_amount
    expense.payment_account = new_account
    expense.expense_date = new_date
    expense.category = new_category
    expense.description = locked_adjustment.new_description

    expense.save(
        update_fields=[
            "amount",
            "payment_account",
            "expense_date",
            "category",
            "description",
            "updated_at",
        ]
    )

    # 10. Mark adjustment approved
    locked_adjustment.status = ExpenseAdjustment.Status.APPROVED
    locked_adjustment.approved_by = approved_by
    locked_adjustment.approved_at = timezone.now()

    locked_adjustment.save(
        update_fields=[
            "status",
            "approved_by",
            "approved_at",
        ]
    )

    # 11. Notify requester after successful commit
    transaction.on_commit(
        lambda: _notify_adjustment_approved(
            requester=locked_adjustment.requested_by,
            adjustment_id=locked_adjustment.id,
            expense_id=expense.id,
            new_amount=locked_adjustment.new_amount,
        )
    )

    return locked_adjustment


@transaction.atomic
def reject_expense_adjustment(
    *,
    adjustment,
    rejected_by,
    rejection_reason,
):
    # 1. Lock adjustment
    locked_adjustment = (
        ExpenseAdjustment.objects
        .select_for_update()
        .get(pk=adjustment.pk)
    )

    # 2. Validate status
    if locked_adjustment.status != ExpenseAdjustment.Status.PENDING:
        raise ValueError(
            "Only pending expense adjustments can be rejected."
        )

    # 3. Validate rejection reason
    if not rejection_reason or not rejection_reason.strip():
        raise ValueError(
            "A rejection reason is required."
        )

    # 4. Record rejection
    locked_adjustment.status = ExpenseAdjustment.Status.REJECTED
    locked_adjustment.rejected_by = rejected_by
    locked_adjustment.rejection_reason = rejection_reason.strip()
    locked_adjustment.rejected_at = timezone.now()

    locked_adjustment.save(
        update_fields=[
            "status",
            "rejected_by",
            "rejection_reason",
            "rejected_at",
        ]
    )

    # 5. Notify requester after successful commit
    transaction.on_commit(
        lambda: _notify_adjustment_rejected(
            requester=locked_adjustment.requested_by,
            adjustment_id=locked_adjustment.id,
            expense_id=locked_adjustment.expense_id,
            rejection_reason=locked_adjustment.rejection_reason,
        )
    )

    return locked_adjustment