from django.db import transaction
from django.db.models import Sum
from rest_framework.exceptions import ValidationError

from ..models import (
    Expense,
    PettyCashLedger,
)


@transaction.atomic
def add_cash(
    amount,
    transaction_date,
    created_by,
    remarks=""
):
    if amount <= 0:
        raise ValidationError(
            "Cash amount must be greater than zero."
        )

    last_entry = (
        PettyCashLedger.objects
        .select_for_update()
        .order_by("-id")
        .first()
    )

    current_balance = (
        last_entry.balance_after
        if last_entry
        else 0
    )

    new_balance = current_balance + amount

    return PettyCashLedger.objects.create(
        transaction_type=PettyCashLedger.TransactionType.CASH_IN,
        amount=amount,
        balance_after=new_balance,
        transaction_date=transaction_date,
        remarks=remarks,
        created_by=created_by,
    )


@transaction.atomic
def create_expense(
    category,
    amount,
    expense_date,
    created_by,
    description=""
):
    if amount <= 0:
        raise ValidationError(
            "Expense amount must be greater than zero."
        )

    last_entry = (
        PettyCashLedger.objects
        .select_for_update()
        .order_by("-id")
        .first()
    )

    current_balance = (
        last_entry.balance_after
        if last_entry
        else 0
    )

    new_balance = current_balance - amount

    expense = Expense.objects.create(
        category=category,
        amount=amount,
        expense_date=expense_date,
        description=description,
        created_by=created_by,
    )

    PettyCashLedger.objects.create(
        transaction_type=PettyCashLedger.TransactionType.EXPENSE,
        amount=-amount,
        balance_after=new_balance,
        transaction_date=expense_date,
        expense=expense,
        remarks=description,
        created_by=created_by,
    )

    return expense

@transaction.atomic
def update_expense(
    expense,
    category,
    amount,
    expense_date,
    updated_by,
    description="",
):
    if amount <= 0:
        raise ValidationError(
            "Expense amount must be greater than zero."
        )

    # Lock the expense row
    expense = (
        Expense.objects
        .select_for_update()
        .get(pk=expense.pk)
    )

    old_amount = expense.amount

    # Difference between new and old amount
    difference = amount - old_amount

    # Update expense
    expense.category = category
    expense.amount = amount
    expense.expense_date = expense_date
    expense.description = description

    expense.save(
        update_fields=[
            "category",
            "amount",
            "expense_date",
            "description",
            "updated_at",
        ]
    )

    # If amount didn't change, no cash adjustment is required
    if difference == 0:
        return expense, None

    # Lock the latest ledger entry
    last_entry = (
        PettyCashLedger.objects
        .select_for_update()
        .order_by("-id")
        .first()
    )

    current_balance = (
        last_entry.balance_after
        if last_entry
        else 0
    )

    # Increase in expense  -> negative difference
    # Decrease in expense  -> positive difference
    new_balance = current_balance - difference

    adjustment = PettyCashLedger.objects.create(
        transaction_type=(
            PettyCashLedger.TransactionType.ADJUSTMENT
        ),
        amount=-difference,
        balance_after=new_balance,
        transaction_date=expense_date,
        expense=expense,
        remarks="Expense amount adjustment",
        created_by=updated_by,
    )

    return expense, adjustment