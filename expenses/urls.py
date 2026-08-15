from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import (
    ExpenseCategoryViewSet,
    ExpenseViewSet,
    PettyCashLedgerView,
    AddPettyCashView,
    PettyCashBalanceView,
    ExpenseReportView,
    MonthlyExpenseReportView,
    DailyExpenseReportView,
    YearlyExpenseReportView
)


router = DefaultRouter()

router.register(
    "categories",
    ExpenseCategoryViewSet,
    basename="expense-category"
)

router.register(
    "expenses",
    ExpenseViewSet,
    basename="expense"
)


urlpatterns = [
    path("", include(router.urls)),

    path(
        "petty-cash/",
        PettyCashLedgerView.as_view(),
        name="petty-cash"
    ),

    path(
        "petty-cash/add/",
        AddPettyCashView.as_view(),
        name="add-petty-cash"
    ),

    path(
        "petty-cash/balance/",
        PettyCashBalanceView.as_view(),
        name="petty-cash-balance"
    ),

    path(
    "reports/",
    ExpenseReportView.as_view(),
    name="expense-report"
    ),

    path(
    "reports/daily/",
    DailyExpenseReportView.as_view(),
    name="daily-expense-report"
    ),

    path(
        "reports/monthly/",
        MonthlyExpenseReportView.as_view(),
        name="monthly-expense-report"
    ),

    path(
        "reports/yearly/",
        YearlyExpenseReportView.as_view(),
        name="yearly-expense-report"
    ),
]