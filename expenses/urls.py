from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import (
    ExpenseCategoryViewSet,
    ExpenseViewSet,
    ExpenseReportView,
    MonthlyExpenseReportView,
    DailyExpenseReportView,
    YearlyExpenseReportView,
    FinancialAccountViewSet,
    TransferViewSet,
    FinancialTransactionViewSet,
    DailySalesViewSet,
    ReceivableSettlementViewSet,
    ReceivableViewSet,
    DeliveryPartnerViewSet,
DeliveryPartnerCommissionRateViewSet,
ExpenseAdjustmentViewSet,
SupplierPaymentViewSet,
SupplierPayableViewSet
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

router.register(
    "accounts",
    FinancialAccountViewSet,
    basename="financial-account",
)

router.register(
    "transfers",
    TransferViewSet,
    basename="transfer",
)


router.register(
    "transactions",
    FinancialTransactionViewSet,
    basename="financial-transaction",
)


router.register(
    "daily-sales",
    DailySalesViewSet,
    basename="daily-sales",
)

router.register(
    "receivable-settlements",
    ReceivableSettlementViewSet,
    basename="receivable-settlement",
)

router.register(
    "receivables",
    ReceivableViewSet,
    basename="receivable",
)


router.register(
    "delivery-partners",
    DeliveryPartnerViewSet,
    basename="delivery-partner",
)

router.register(
    "delivery-partner-rates",
    DeliveryPartnerCommissionRateViewSet,
    basename="delivery-partner-rate",
)

router.register(
    r"expense-adjustments",
    ExpenseAdjustmentViewSet,
)

router.register(
    r"supplier-payments",
    SupplierPaymentViewSet,
    basename="supplier-payment",
)

router.register(
    r"supplier-payables",
    SupplierPayableViewSet,
    basename="supplier-payable"
)

urlpatterns = [
    path("", include(router.urls)),


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