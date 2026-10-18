from django.db import transaction

from expenses.models import Expense, FinancialTransaction
from expenses.services.financial_transaction_service import (
    create_financial_transaction,
)
from notifications.services.notification_service import (
    notify_admins_and_managers,
)


def _notify_expense_created(
    *,
    branch,
    amount,
    expense_id,
):
    """
    Notify admins and managers after an expense is committed.
    Notification failures must not affect the financial operation.
    """
    try:
        notify_admins_and_managers(
            notification_type="INFO",
            title="Expense Recorded",
            message=(
                f"An expense of ₹{amount} has been recorded "
                f"successfully. Expense ID: {expense_id}."
            ),
            module="FINANCE",
            object_id=expense_id,
            branch=branch,
        )
    except Exception:
        # Do not undo a successful financial operation
        # if notification creation fails.
        import logging

        logger = logging.getLogger(__name__)
        logger.exception(
            "Failed to send expense notification for Expense ID %s",
            expense_id,
        )


@transaction.atomic
def create_expense(
    *,
    branch,
    category,
    payment_account,
    amount,
    expense_date,
    created_by,
    description="",
):
    # 1. Create the expense
    expense = Expense.objects.create(
        branch=branch,
        category=category,
        payment_account=payment_account,
        amount=amount,
        expense_date=expense_date,
        description=description,
        created_by=created_by,
    )

    # 2. Create the corresponding financial transaction
    create_financial_transaction(
        branch=branch,
        account=payment_account,
        transaction_type=FinancialTransaction.TransactionType.EXPENSE,
        direction=FinancialTransaction.Direction.OUT,
        amount=amount,
        transaction_date=expense_date,
        created_by=created_by,
        description=description,
        reference=f"EXPENSE-{expense.id}",
    )

    # 3. Send the notification only after the transaction commits
    transaction.on_commit(
        lambda: _notify_expense_created(
            branch=branch,
            amount=amount,
            expense_id=expense.id,
        )
    )

    return expense