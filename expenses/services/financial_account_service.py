import logging
from decimal import Decimal

from django.db import transaction
from django.db.models import Sum

from expenses.models import (
    FinancialAccount,
    FinancialTransaction,
)

from notifications.services.notification_service import (
    notify_admins_and_managers,
)

logger = logging.getLogger(__name__)


def _notify_financial_account_created(
    *,
    branch,
    account_id,
    account_name,
    account_type,
    opening_balance,
    created_by,
):
    """Notify admins and branch managers about a new account."""
    try:
        notify_admins_and_managers(
            notification_type="INFO",
            title="Financial Account Created",
            message=(
                f"Financial account '{account_name}' has been created. "
                f"Type: {account_type}. "
                f"Opening balance: ₹{opening_balance}. "
                f"Created by: {created_by}."
            ),
            module="FINANCE",
            object_id=account_id,
            branch=branch,
        )
    except Exception:
        logger.exception(
            "Failed to notify about financial account ID %s",
            account_id,
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
    # 1. Validate opening balance
    if opening_balance < Decimal("0.00"):
        raise ValueError(
            "Opening balance cannot be negative."
        )

    # 2. Create financial account
    account = FinancialAccount.objects.create(
        branch=branch,
        name=name,
        account_type=account_type,
        account_purpose=account_purpose,
        opening_balance=opening_balance,
        opening_balance_date=opening_balance_date,
        created_by=created_by,
    )

    # 3. Record opening balance transaction when positive
    if opening_balance > Decimal("0.00"):
        FinancialTransaction.objects.create(
            branch=branch,
            account=account,
            transaction_type=(
                FinancialTransaction.TransactionType.OPENING_BALANCE
            ),
            direction=FinancialTransaction.Direction.IN,
            amount=opening_balance,
            transaction_date=opening_balance_date,
            description="Opening balance",
            created_by=created_by,
        )

    # 4. Notify only after the database transaction commits
    transaction.on_commit(
        lambda: _notify_financial_account_created(
            branch=account.branch,
            account_id=account.id,
            account_name=account.name,
            account_type=account.account_type,
            opening_balance=account.opening_balance,
            created_by=str(created_by),
        )
    )

    return account


def get_account_balance(account):
    """
    Calculate the current balance of a financial account.

    The opening balance is stored on the account.
    Its OPENING_BALANCE transaction is a historical record
    and must not be counted again.
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
        or Decimal("0.00")
    )

    money_out = (
        transactions
        .filter(
            direction=FinancialTransaction.Direction.OUT
        )
        .aggregate(
            total=Sum("amount")
        )["total"]
        or Decimal("0.00")
    )

    return opening_balance + money_in - money_out