from decimal import Decimal

from django.db.models import Sum, Count, Q
from django.utils import timezone

from organization.services.access_service import get_accessible_branches
from employees.models import Employee
from attendance.models import Attendance
from expenses.models import (
    DailySales,
    Expense,
    FinancialAccount,
    FinancialTransaction,
    SupplierPayable,
    Receivable,
    ExpenseCategory,
)
from inventory.models import Product, StockBalance
from expenses.services.financial_account_service import get_account_balance


def money(value):
    """Return a consistent decimal value."""
    return value or Decimal("0.00")


def get_dashboard_data(
    user,
    month=None,
    year=None,
    branch_id=None,
):
    today = timezone.localdate()

    month = month or today.month
    year = year or today.year

    if month < 1 or month > 12:
        raise ValueError("Month must be between 1 and 12.")

    if year < 2000 or year > today.year + 1:
        raise ValueError("Invalid year.")

    branches = get_accessible_branches(user)

    if branch_id is not None:
        branches = branches.filter(id=branch_id)

    branch_ids = list(
        branches.values_list("id", flat=True)
    )
    # --------------------------------------------------
    # DATE RANGE
    # --------------------------------------------------

    from datetime import date
    import calendar

    start_date = date(year, month, 1)
    end_date = date(
        year,
        month,
        calendar.monthrange(year, month)[1],
    )

    # --------------------------------------------------
    # REVENUE: POSTED DAILY SALES ONLY
    # --------------------------------------------------

    sales = DailySales.objects.filter(
        branch_id__in=branch_ids,
        business_date__range=(start_date, end_date),
        status=DailySales.Status.POSTED,
    )

    total_revenue = money(
        sales.aggregate(total=Sum("total_gross"))["total"]
    )

    # --------------------------------------------------
    # EXPENSES
    # --------------------------------------------------

    expenses = Expense.objects.filter(
        branch_id__in=branch_ids,
        expense_date__range=(start_date, end_date),
    )

    total_expenses = money(
        expenses.aggregate(total=Sum("amount"))["total"]
    )

    # This is a preliminary operating result, not final
    # accounting profit.
    operating_result = total_revenue - total_expenses

    # Preliminary operating profit.
    operating_profit = operating_result

    # Profit margin as a percentage of revenue.
    profit_margin = (
        (operating_profit / total_revenue) * Decimal("100")
        if total_revenue > 0
        else Decimal("0.00")
    )

    # Revenue remaining after recorded expenses.
    profit_margin = profit_margin.quantize(
        Decimal("0.01")
    )
    # --------------------------------------------------
    # CASH / BANK / UPI / PETTY CASH BALANCES
    # --------------------------------------------------

    accounts = FinancialAccount.objects.filter(
        branch_id__in=branch_ids,
        is_active=True,
        account_type__in=[
            "CASH",
            "BANK",
            "UPI",
            "PETTY_CASH",
        ],
    )

    cash_balance = sum(
        (
            get_account_balance(account)
            for account in accounts
        ),
        Decimal("0.00"),
    )

    # --------------------------------------------------
    # SUPPLIER PAYABLES
    # --------------------------------------------------

    payables = SupplierPayable.objects.filter(
        branch_id__in=branch_ids,
        outstanding_amount__gt=0,
    )

    pending_payables = money(
        payables.aggregate(
            total=Sum("outstanding_amount")
        )["total"]
    )

    # --------------------------------------------------
    # DELIVERY RECEIVABLES
    # --------------------------------------------------

    receivables = Receivable.objects.filter(
        branch_id__in=branch_ids,
        outstanding_amount__gt=0,
    )

    pending_receivables = money(
        receivables.aggregate(
            total=Sum("outstanding_amount")
        )["total"]
    )

    # --------------------------------------------------
    # INVENTORY / LOW STOCK
    # --------------------------------------------------

    products = Product.objects.filter(is_active=True)

    stock_balances = StockBalance.objects.filter(
        branch_id__in=branch_ids,
        product__is_active=True,
    ).values("product_id").annotate(
        current_stock=Sum("quantity"),
    )

    stock_lookup = {
        row["product_id"]: row["current_stock"]
        for row in stock_balances
    }

    low_stock_count = 0
    out_of_stock_count = 0

    for product in products:
        quantity = stock_lookup.get(
            product.id,
            Decimal("0.00"),
        )

        if quantity <= 0:
            out_of_stock_count += 1
        elif quantity <= product.minimum_stock:
            low_stock_count += 1

    # --------------------------------------------------
    # EMPLOYEE ATTENDANCE FOR TODAY
    # --------------------------------------------------

    employees = Employee.objects.filter(
        branch_id__in=branch_ids,
        is_active=True,
    )

    attendance = Attendance.objects.filter(
        employee__branch_id__in=branch_ids,
        employee__is_active=True,
        date=today,
    )

    attendance_summary = {
        "present": attendance.filter(
            status=Attendance.Status.PRESENT
        ).count(),
        "absent": attendance.filter(
            status=Attendance.Status.ABSENT
        ).count(),
        "half_day": attendance.filter(
            status=Attendance.Status.HALF_DAY
        ).count(),
        "leave": attendance.filter(
            status=Attendance.Status.LEAVE
        ).count(),
        "total_active_employees": employees.count(),
        "records_entered": attendance.count(),
    }

    # --------------------------------------------------
    # EXPENSE BREAKDOWN
    # --------------------------------------------------

    expense_breakdown = list(
        expenses.values(
            "category_id",
            "category__name",
        ).annotate(
            total=Sum("amount"),
        ).order_by("-total")
    )

    expense_breakdown = [
        {
            "category_id": row["category_id"],
            "category": row["category__name"],
            "amount": money(row["total"]),
        }
        for row in expense_breakdown
    ]

    # --------------------------------------------------
    # BRANCH PERFORMANCE
    # --------------------------------------------------

    branch_performance = []

    for branch in branches:
        branch_revenue = money(
            sales.filter(
                branch_id=branch.id
            ).aggregate(
                total=Sum("total_gross")
            )["total"]
        )

        branch_expenses = money(
            expenses.filter(
                branch_id=branch.id
            ).aggregate(
                total=Sum("amount")
            )["total"]
        )

        branch_performance.append({
            "branch_id": branch.id,
            "branch_name": branch.name,
            "revenue": branch_revenue,
            "expenses": branch_expenses,
            "operating_result": (
                branch_revenue - branch_expenses
            ),
        })

    return {
        "period": {
            "month": month,
            "year": year,
            "start_date": start_date,
            "end_date": end_date,
        },
        "financial_summary": {
            "monthly_revenue": total_revenue,
            "monthly_expenses": total_expenses,
            "operating_result": operating_result,
            "operating_profit": operating_profit,
            "profit_margin_percentage": profit_margin,
            "cash_and_bank_balance": cash_balance,
            "pending_supplier_payables": pending_payables,
            "pending_delivery_receivables": pending_receivables,
        },
        "inventory_summary": {
            "low_stock_products": low_stock_count,
            "out_of_stock_products": out_of_stock_count,
        },
        "attendance_summary": attendance_summary,
        "expense_breakdown": expense_breakdown,
        "branch_performance": branch_performance,
    }
