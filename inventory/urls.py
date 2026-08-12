from rest_framework.routers import DefaultRouter,path

from .views import SupplierViewSet, ProductViewSet , PurchaseViewSet,StockUsageViewSet,LiveStockView,StockLedgerView,SupplierPurchaseHistoryView


router = DefaultRouter()

router.register(
    "suppliers",
    SupplierViewSet,
    basename="supplier"
)

router.register(
    "products",
    ProductViewSet,
    basename="product"
)

router.register(
    "purchases",
    PurchaseViewSet,
    basename="purchase"
)


router.register(
    "usages",
    StockUsageViewSet,
    basename="usage"
)


urlpatterns = router.urls + [
    path(
        "stock/",
        LiveStockView.as_view(),
        name="live-stock"
    ),

    path(
    "stock/ledger/",
    StockLedgerView.as_view(),
    name="stock-ledger"
    ),
    path(
    "suppliers/<int:supplier_id>/purchases/",
    SupplierPurchaseHistoryView.as_view(),
    name="supplier-purchase-history"
    ),
]