from rest_framework import viewsets
from .services.usage_service import process_usage
from .services.stock_service import get_live_stock,get_stock_ledger
from .models import Supplier, Product, Purchase ,StockUsage,StockLedger
from .serializers import (
    SupplierSerializer,
    ProductSerializer,
    PurchaseSerializer,
    StockUsageSerializer,
    StockSerializer,
    StockLedgerSerializer,
    SupplierPurchaseHistorySerializer
)
from rest_framework.views import APIView
from rest_framework.response import Response
from .services.purchase_service import (
    get_supplier_purchase_history
)
from .pagination import StandardPagination


class SupplierViewSet(viewsets.ModelViewSet):

    queryset = Supplier.objects.all()
    serializer_class = SupplierSerializer
    pagination_class = StandardPagination

class ProductViewSet(viewsets.ModelViewSet):

    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    pagination_class = StandardPagination

class PurchaseViewSet(viewsets.ModelViewSet):

    queryset = Purchase.objects.prefetch_related(
        "items"
    ).select_related(
        "supplier"
    )

    serializer_class = PurchaseSerializer    
    pagination_class = StandardPagination


class StockUsageViewSet(viewsets.ModelViewSet):

    queryset = StockUsage.objects.select_related(
        "product"
    ).all()

    pagination_class = StandardPagination
    serializer_class = StockUsageSerializer
    def perform_create(self, serializer):

        usage = serializer.save()

        process_usage(usage)    


        # live stock --------------------------------  


class LiveStockView(APIView):

    def get(self, request):

        stock_data = get_live_stock(
            request.query_params
        )

        serializer = StockSerializer(
            stock_data,
            many=True
        )

        return Response(serializer.data)


    # ---------------------------------------------------------------------------------------------- 


class StockLedgerView(APIView):

    pagination_class = StandardPagination

    def get(self, request):

        ledger = get_stock_ledger(
            request.query_params
        )

        paginator = self.pagination_class()

        page = paginator.paginate_queryset(
            ledger,
            request
        )

        serializer = StockLedgerSerializer(
            page,
            many=True
        )

        return paginator.get_paginated_response(
            serializer.data
        )


    # -----------------------------------------------------------------------------  





class SupplierPurchaseHistoryView(APIView):

    pagination_class = StandardPagination

    def get(self, request, supplier_id):

        purchase_items = get_supplier_purchase_history(
            supplier_id
        )

        paginator = self.pagination_class()

        page = paginator.paginate_queryset(
            purchase_items,
            request
        )

        serializer = SupplierPurchaseHistorySerializer(
            page,
            many=True
        )

        return paginator.get_paginated_response(
            serializer.data
        )