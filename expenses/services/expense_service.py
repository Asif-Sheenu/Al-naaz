from django.db import transaction

from expenses.models import Expense, FinancialTransaction
from expenses.services.financial_transaction_service import (
    create_financial_transaction,
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

    return expense