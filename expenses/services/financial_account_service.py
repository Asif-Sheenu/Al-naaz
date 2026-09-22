from decimal import Decimal

from django.db import transaction
from django.db.models import Sum
from expenses.models import (
    FinancialAccount,
    FinancialTransaction,
)


@transaction.atomic
def create_financial_account(
    *,
    branch,
    name,
    account_type,
    account_purpose,
    opening_balance,
    opening_balance_date,
    created_by,
):

    if opening_balance < Decimal("0.00"):
        raise ValueError(
            "Opening balance cannot be negative."
        )

    account = FinancialAccount.objects.create(
        branch=branch,
        name=name,
        account_type=account_type,
        account_purpose=account_purpose,
        opening_balance=opening_balance,
        opening_balance_date=opening_balance_date,
        created_by=created_by,
    )

    if opening_balance > Decimal("0.00"):

        FinancialTransaction.objects.create(
            branch=branch,
            account=account,
            transaction_type=(
                FinancialTransaction.TransactionType.OPENING_BALANCE
            ),
            direction=(
                FinancialTransaction.Direction.IN
            ),
            amount=opening_balance,
            transaction_date=opening_balance_date,
            description="Opening balance",
            created_by=created_by,
        )

    return account


def get_account_balance(account):
    """
    Calculate the current balance of a financial account.

    Opening balance is stored on the account.
    OPENING_BALANCE transaction is only the historical record
    of that opening balance, so it is not counted again.
    """

    opening_balance = account.opening_balance

    transactions = FinancialTransaction.objects.filter(
        account=account
    ).exclude(
        transaction_type=(
            FinancialTransaction.TransactionType.OPENING_BALANCE
        )
    )

    money_in = (
        transactions
        .filter(
            direction=FinancialTransaction.Direction.IN
        )
        .aggregate(
            total=Sum("amount")
        )["total"]
        or 0
    )

    money_out = (
        transactions
        .filter(
            direction=FinancialTransaction.Direction.OUT
        )
        .aggregate(
            total=Sum("amount")
        )["total"]
        or 0
    )

    return opening_balance + money_in - money_out