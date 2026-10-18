from datetime import date, timedelta
from decimal import Decimal

from django.db.models import Sum
from django.utils import timezone

from expenses.models import (
    FinancialAccount,
    FinancialTransaction,
    Receivable,
    SupplierPayable,
)
from expenses.services.financial_account_service import (
    get_account_balance,
)


ZERO = Decimal("0.00")


def get_period_dates(period):
    """
    Return the start and end dates for a dashboard reporting period.
    """

    today = timezone.localdate()

    if period == "today":
        return today, today

    if period == "week":
        start_date = today - timedelta(days=today.weekday())
        return start_date, today

    if period == "month":
        return today.replace(day=1), today

    if period == "year":
        return today.replace(month=1, day=1), today

    if period == "all":
        return None, today

    raise ValueError(
        "Invalid period. Choose today, week, month, year, or all."
    )


def money(value):
    """
    Ensure monetary values are returned as Decimal values.
    """

    return value if value is not None else ZERO


def get_finance_dashboard(*, branches, period="month"):
    """
    Generate the complete Finance Overview dashboard response.

    `branches` must already contain only branches the user is
    authorized to access.
    """

    start_date, end_date = get_period_dates(period)

    branch_ids = list(
        branches.values_list("id", flat=True)
    )

    accounts = (
        FinancialAccount.objects
        .filter(branch_id__in=branch_ids)
        .select_related("branch")
        .order_by("branch__name", "name")
    )

    transactions = FinancialTransaction.objects.filter(
        branch_id__in=branch_ids,
        transaction_date__lte=end_date,
    )

    if start_date:
        period_transactions = transactions.filter(
            transaction_date__gte=start_date
        )
    else:
        period_transactions = transactions

    # --------------------------------------------------
    # 1. Account balances
    # --------------------------------------------------

    account_balances = []
    available_money = ZERO
    total_receivables = ZERO

    for account in accounts:
        balance = money(get_account_balance(account))

        account_balances.append({
            "account_id": account.id,
            "account_name": account.name,
            "account_type": account.account_type,
            "branch_id": account.branch_id,
            "branch_name": account.branch.name,
            "balance": balance,
            "is_active": account.is_active,
        })

        if account.account_type in {
            FinancialAccount.AccountType.CASH,
            FinancialAccount.AccountType.BANK,
            FinancialAccount.AccountType.UPI,
            FinancialAccount.AccountType.PETTY_CASH,
        }:
            available_money += balance

        elif (
            account.account_type
            == FinancialAccount.AccountType.RECEIVABLE
        ):
            total_receivables += balance

    # --------------------------------------------------
    # 2. Pending receivables
    # --------------------------------------------------

    receivables = (
        Receivable.objects
        .filter(
            branch_id__in=branch_ids,
            outstanding_amount__gt=ZERO,
        )
        .select_related(
            "branch",
            "receivable_account",
            "delivery_partner",
        )
        .order_by("business_date", "id")
    )

    pending_receivables = [
        {
            "id": item.id,
            "branch_id": item.branch_id,
            "branch_name": item.branch.name,
            "account_id": item.receivable_account_id,
            "account_name": item.receivable_account.name,
            "platform": item.platform,
            "outstanding_amount": item.outstanding_amount,
            "status": item.status,
            "business_date": item.business_date,
        }
        for item in receivables
    ]

    # Use outstanding receivable records as the authoritative
    # dashboard total to avoid counting the same receivable twice.
    total_receivables = sum(
        (
            item["outstanding_amount"]
            for item in pending_receivables
        ),
        ZERO,
    )

    # --------------------------------------------------
    # 3. Pending supplier payables
    # --------------------------------------------------

    payables = (
        SupplierPayable.objects
        .filter(
            branch_id__in=branch_ids,
            outstanding_amount__gt=ZERO,
        )
        .select_related("branch", "supplier")
        .order_by("created_at", "id")
    )

    pending_payables = [
        {
            "id": item.id,
            "branch_id": item.branch_id,
            "branch_name": item.branch.name,
            "supplier_id": item.supplier_id,
            "supplier_name": item.supplier.name,
            "total_amount": item.total_amount,
            "paid_amount": item.paid_amount,
            "outstanding_amount": item.outstanding_amount,
            "status": item.status,
        }
        for item in payables
    ]

    total_payables = sum(
        (
            item["outstanding_amount"]
            for item in pending_payables
        ),
        ZERO,
    )

    # --------------------------------------------------
    # 4. Income vs expenses
    # --------------------------------------------------

    revenue = money(
        period_transactions.filter(
            transaction_type=(
                FinancialTransaction.TransactionType.REVENUE
            )
        ).aggregate(total=Sum("amount"))["total"]
    )

    expenses = money(
        period_transactions.filter(
            transaction_type__in=[
                FinancialTransaction.TransactionType.EXPENSE,
                FinancialTransaction.TransactionType.ASSET_PURCHASE,
            ]
        ).aggregate(total=Sum("amount"))["total"]
    )

    # --------------------------------------------------
    # 5. Recent transactions
    # --------------------------------------------------

    recent = (
        transactions
        .select_related("account", "branch")
        .order_by("-transaction_date", "-id")[:10]
    )

    recent_transactions = [
        {
            "id": item.id,
            "date": item.transaction_date,
            "description": item.description,
            "reference": item.reference,
            "account_id": item.account_id,
            "account_name": item.account.name,
            "branch_id": item.branch_id,
            "branch_name": item.branch.name,
            "transaction_type": item.transaction_type,
            "direction": item.direction,
            "amount": item.amount,
        }
        for item in recent
    ]

    # --------------------------------------------------
    # 6. Cash flow summary
    # --------------------------------------------------

    inflow = money(
        period_transactions.filter(
            direction=FinancialTransaction.Direction.IN,
        ).exclude(
            transaction_type=(
                FinancialTransaction.TransactionType.TRANSFER_IN
            )
        ).aggregate(total=Sum("amount"))["total"]
    )

    outflow = money(
        period_transactions.filter(
            direction=FinancialTransaction.Direction.OUT,
        ).exclude(
            transaction_type=(
                FinancialTransaction.TransactionType.TRANSFER_OUT
            )
        ).aggregate(total=Sum("amount"))["total"]
    )

    # --------------------------------------------------
    # 7. Overall financial position
    # --------------------------------------------------

    total_financial_position = (
        available_money
        + total_receivables
        - total_payables
    )

    # --------------------------------------------------
    # 8. Final dashboard response
    # --------------------------------------------------

    return {
        "period": period,

        "overview": {
            "total_financial_position": total_financial_position,
            "available_money": available_money,
            "receivables": total_receivables,
            "payables": total_payables,
            "pending_receivables_count": len(pending_receivables),
            "pending_payables_count": len(pending_payables),
        },

        "account_balances": account_balances,

        "income_expenses": {
            "total_income": revenue,
            "total_expenses": expenses,
            "net_income": revenue - expenses,
            "start_date": start_date,
            "end_date": end_date,
        },

        "recent_transactions": recent_transactions,

        "pending_receivables": pending_receivables,

        "pending_payables": pending_payables,

        "cash_flow": {
            "total_inflow": inflow,
            "total_outflow": outflow,
            "net_cash_flow": inflow - outflow,
            "start_date": start_date,
            "end_date": end_date,
        },
    }