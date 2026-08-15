from django.db.models import Sum, DecimalField
from django.db.models.functions import Coalesce

from ..models import Expense, PettyCashLedger


def get_expense_report(start_date, end_date):

    expenses = Expense.objects.filter(
        expense_date__range=[
            start_date,
            end_date
        ]
    )

    decimal_field = DecimalField(
        max_digits=12,
        decimal_places=2
    )

    # Total expenses
    total_expense = expenses.aggregate(
        total=Coalesce(
            Sum("amount"),
            0,
            output_field=decimal_field
        )
    )["total"]

    # Total cash added
    total_cash_added = PettyCashLedger.objects.filter(
        transaction_type="CASH_IN",
        transaction_date__range=[
            start_date,
            end_date
        ]
    ).aggregate(
        total=Coalesce(
            Sum("amount"),
            0,
            output_field=decimal_field
        )
    )["total"]

    expense_count = expenses.count()

    # Balance before the report period
    previous_entry = (
        PettyCashLedger.objects
        .filter(
            transaction_date__lt=start_date
        )
        .order_by("-id")
        .first()
    )

    opening_balance = (
        previous_entry.balance_after
        if previous_entry
        else 0
    )

    # Balance at the end of the report period
    closing_entry = (
        PettyCashLedger.objects
        .filter(
            transaction_date__lte=end_date
        )
        .order_by("-id")
        .first()
    )

    closing_balance = (
        closing_entry.balance_after
        if closing_entry
        else 0
    )

    # Category-wise expenses
    category_totals = (
        expenses
        .values(
            "category_id",
            "category__name"
        )
        .annotate(
            total=Coalesce(
                Sum("amount"),
                0,
                output_field=decimal_field
            )
        )
        .order_by("-total")
    )

    # Clean API response
    category_totals = [
        {
            "category_id": item["category_id"],
            "category_name": item["category__name"],
            "total": item["total"],
        }
        for item in category_totals
    ]

    return {
        "start_date": start_date,
        "end_date": end_date,
        "opening_balance": opening_balance,
        "total_cash_added": total_cash_added,
        "total_expense": total_expense,
        "expense_count": expense_count,
        "closing_balance": closing_balance,
        "category_totals": category_totals,
    }