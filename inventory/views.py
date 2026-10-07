from django.db import transaction
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiTypes
from rest_framework import viewsets, mixins,status
from rest_framework.views import APIView
from rest_framework.response import Response

from .models import (
    Supplier,
    Product,
    Purchase,
    StockUsage,
    StockAdjustment,
)
from core.cache.service import delete_pattern
from .services.idempotency_service import (
    start_idempotent_operation,
    complete_idempotent_operation,
    IdempotencyConflict,
)
from .services.adjustment_service import process_stock_adjustment
from .serializers import (
    SupplierSerializer,
    ProductSerializer,
    PurchaseSerializer,
    StockUsageSerializer,
    StockAdjustmentSerializer,
    StockSerializer,
    StockLedgerSerializer,
    SupplierPurchaseHistorySerializer,
)

from .services.usage_service import process_usage

from .services.stock_service import (
    get_live_stock,
    get_stock_ledger,
)

from .services.purchase_service import (
    get_supplier_purchase_history,
)

from .pagination import StandardPagination

from organization.services.access_service import (
    get_accessible_branches,
)

from notifications.services.audit_service import log_activity

from .permissions import (
    CanViewInventory,
    CanCreatePurchase,
    CanCreateStockUsage,
)


# ============================================================
# SUPPLIER
# ============================================================

class SupplierViewSet(viewsets.ModelViewSet):

    queryset = Supplier.objects.all()

    serializer_class = SupplierSerializer

    pagination_class = StandardPagination

    permission_classes = [
        CanViewInventory
    ]


# ============================================================
# PRODUCT
# ============================================================

class ProductViewSet(viewsets.ModelViewSet):

    queryset = Product.objects.all()

    serializer_class = ProductSerializer

    pagination_class = StandardPagination

    permission_classes = [
        CanViewInventory
    ]


class PurchaseViewSet(
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):

    queryset = (
        Purchase.objects
        .prefetch_related(
            "items__product"
        )
        .select_related(
            "supplier",
            "branch",
            "created_by",
        )
    )

    serializer_class = PurchaseSerializer

    pagination_class = StandardPagination

    permission_classes = [
        CanCreatePurchase
    ]

    def get_queryset(self):

        queryset = super().get_queryset()

        user = self.request.user

        # ADMIN / superuser can access all branches
        if (
            user.is_superuser
            or user.role == "ADMIN"
        ):
            return queryset

        accessible_branches = (
            get_accessible_branches(user)
        )

        return queryset.filter(
            branch__in=accessible_branches
        )
    @extend_schema(
    parameters=[
        OpenApiParameter(
            name="Idempotency-Key",
            type=OpenApiTypes.STR,
            location=OpenApiParameter.HEADER,
            required=True,
            description="Unique key used to safely retry purchase creation.",
        )
    ]
    )
    def create(self, request, *args, **kwargs):

        operation = "inventory.purchase.create"

        with transaction.atomic():

            record, created = start_idempotent_operation(
                request=request,
                operation=operation,
            )

            if not created:

                purchase = (
                    self.get_queryset()
                    .filter(
                        pk=record.resource_id
                    )
                    .first()
                )

                if not purchase:

                    raise IdempotencyConflict(
                        "The original purchase no longer exists."
                    )

                serializer = self.get_serializer(
                    purchase
                )

                return Response(
                    serializer.data,
                    status=(
                        record.response_status_code
                        or status.HTTP_201_CREATED
                    ),
                )

            
            response = super().create(
                request,
                *args,
                **kwargs,
            )

            purchase = getattr(
                self,
                "_created_purchase",
                None,
            )

            if not purchase:

                raise IdempotencyConflict(
                    "Purchase creation did not return a resource."
                )

           

            complete_idempotent_operation(
                record=record,
                resource_type="Purchase",
                resource_id=purchase.id,
                response_status_code=response.status_code,
            )

            return response

    def perform_create(self, serializer):

        purchase = serializer.save()

        self._created_purchase = purchase

       
        items_data = []

        for item in purchase.items.select_related(
            "product"
        ):

            items_data.append({
                "product": item.product.name,
                "quantity": str(item.quantity),
                "unit_price": str(item.unit_price),
                "total_price": str(item.total_price),
            })

        log_activity(
            user=self.request.user,
            action="CREATE",
            module="PURCHASE",
            object_id=purchase.id,
            description=(
                f"Created purchase from "
                f"{purchase.supplier.name}"
            ),
            new_data={
                "supplier": purchase.supplier.name,
                "branch": purchase.branch.name,
                "purchase_date": str(
                    purchase.purchase_date
                ),
                "invoice_number": (
                    purchase.invoice_number
                ),
                "remarks": purchase.remarks,
                "items": items_data,
            },
        )


class StockUsageViewSet(
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):

    queryset = (
        StockUsage.objects
        .select_related(
            "product",
            "branch",
            "created_by",
        )
        .all()
    )

    pagination_class = StandardPagination

    serializer_class = StockUsageSerializer

    permission_classes = [
        CanCreateStockUsage
    ]

    def get_queryset(self):

        queryset = super().get_queryset()

        user = self.request.user

        # ADMIN / superuser can access all branches
        if (
            user.is_superuser
            or user.role == "ADMIN"
        ):
            return queryset

        accessible_branches = (
            get_accessible_branches(user)
        )

        return queryset.filter(
            branch__in=accessible_branches
        )

    @extend_schema(
        parameters=[
            OpenApiParameter(
                name="Idempotency-Key",
                type=OpenApiTypes.STR,
                location=OpenApiParameter.HEADER,
                required=True,
                description="Unique key used to safely retry stock usage creation.",
            )
        ]
    )
    def create(self, request, *args, **kwargs):

        operation = "inventory.stock_usage.create"

        with transaction.atomic():

            record, created = start_idempotent_operation(
                request=request,
                operation=operation,
            )

            # Existing completed request → return original usage
            if not created:

                usage = (
                    self.get_queryset()
                    .filter(
                        pk=record.resource_id
                    )
                    .first()
                )

                if not usage:

                    raise IdempotencyConflict(
                        "The original stock usage no longer exists."
                    )

                serializer = self.get_serializer(
                    usage
                )

                return Response(
                    serializer.data,
                    status=(
                        record.response_status_code
                        or status.HTTP_201_CREATED
                    ),
                )

            # First request
            response = super().create(
                request,
                *args,
                **kwargs,
            )

            usage = getattr(
                self,
                "_created_usage",
                None,
            )

            if not usage:

                raise IdempotencyConflict(
                    "Stock usage creation did not return a resource."
                )

            complete_idempotent_operation(
                record=record,
                resource_type="StockUsage",
                resource_id=usage.id,
                response_status_code=response.status_code,
            )

            return response

    def perform_create(self, serializer):

        usage = serializer.save()

        process_usage(usage)

        self._created_usage = usage

# ============================================================
# STOCK ADJUSTMENT
# ============================================================

class StockAdjustmentViewSet(
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):

    queryset = (
        StockAdjustment.objects
        .select_related(
            "product",
            "branch",
            "created_by",
        )
        .all()
    )

    serializer_class = StockAdjustmentSerializer

    pagination_class = StandardPagination

    permission_classes = [
        CanCreateStockUsage
    ]

    def get_queryset(self):

        queryset = super().get_queryset()

        user = self.request.user

        # ADMIN / superuser can access all branches
        if (
            user.is_superuser
            or user.role == "ADMIN"
        ):
            return queryset

        accessible_branches = get_accessible_branches(user)

        return queryset.filter(
            branch__in=accessible_branches
        )

    @extend_schema(
        parameters=[
            OpenApiParameter(
                name="Idempotency-Key",
                type=OpenApiTypes.STR,
                location=OpenApiParameter.HEADER,
                required=True,
                description=(
                    "Unique key used to safely retry "
                    "stock adjustment creation."
                ),
            )
        ]
    )
    def create(self, request, *args, **kwargs):

        operation = "inventory.stock_adjustment.create"

        with transaction.atomic():

            record, created = start_idempotent_operation(
                request=request,
                operation=operation,
            )

            # ------------------------------------------------
            # Existing completed request
            # ------------------------------------------------

            if not created:

                adjustment = (
                    self.get_queryset()
                    .filter(
                        pk=record.resource_id
                    )
                    .first()
                )

                if not adjustment:

                    raise IdempotencyConflict(
                        "The original stock adjustment "
                        "no longer exists."
                    )

                serializer = self.get_serializer(
                    adjustment
                )

                return Response(
                    serializer.data,
                    status=(
                        record.response_status_code
                        or status.HTTP_201_CREATED
                    ),
                )

            # ------------------------------------------------
            # First request
            # ------------------------------------------------

            response = super().create(
                request,
                *args,
                **kwargs,
            )

            adjustment = getattr(
                self,
                "_created_adjustment",
                None,
            )

            if not adjustment:

                raise IdempotencyConflict(
                    "Stock adjustment creation "
                    "did not return a resource."
                )

            complete_idempotent_operation(
                record=record,
                resource_type="StockAdjustment",
                resource_id=adjustment.id,
                response_status_code=response.status_code,
            )

            return response

    def perform_create(self, serializer):

        adjustment = serializer.save()

        process_stock_adjustment(
            adjustment=adjustment
        )

        self._created_adjustment = adjustment


class LiveStockView(APIView):

    permission_classes = [
        CanViewInventory
    ]

    def get(self, request):

        params = request.query_params.copy()

        user = request.user

        # ----------------------------------------------------
        # Branch access protection
        # ----------------------------------------------------

        requested_branch = params.get("branch")

        if not (
            user.is_superuser
            or user.role == "ADMIN"
        ):

            accessible_branches = (
                get_accessible_branches(user)
            )

            if requested_branch:

                if not accessible_branches.filter(
                    id=requested_branch
                ).exists():

                    return Response(
                        {
                            "detail": (
                                "You do not have access "
                                "to this branch."
                            )
                        },
                        status=403,
                    )

            else:

                # Non-admin users should not receive
                # stock across inaccessible branches.
                #
                # Use the first/current accessible branch
                # only when no branch was specified.
                branch_ids = list(
                    accessible_branches.values_list(
                        "id",
                        flat=True,
                    )
                )

                if not branch_ids:
                    return Response([])

                # get_live_stock currently accepts one
                # branch, so for non-admin use the user's
                # accessible branch when only one exists.
                if len(branch_ids) == 1:
                    params["branch"] = branch_ids[0]

        stock_data = get_live_stock(params)

        serializer = StockSerializer(
            stock_data,
            many=True,
        )

        return Response(
            serializer.data
        )


# ============================================================
# STOCK LEDGER
# ============================================================

class StockLedgerView(APIView):

    permission_classes = [
        CanViewInventory
    ]

    pagination_class = StandardPagination

    def get(self, request):

        params = request.query_params.copy()

        user = request.user

        requested_branch = params.get(
            "branch"
        )

        # ----------------------------------------------------
        # Branch access protection
        # ----------------------------------------------------

        if not (
            user.is_superuser
            or user.role == "ADMIN"
        ):

            accessible_branches = (
                get_accessible_branches(user)
            )

            if requested_branch:

                if not accessible_branches.filter(
                    id=requested_branch
                ).exists():

                    return Response(
                        {
                            "detail": (
                                "You do not have access "
                                "to this branch."
                            )
                        },
                        status=403,
                    )

            else:

                # Restrict ledger to accessible branches.
                params.setlist(
                    "branch",
                    list(
                        accessible_branches.values_list(
                            "id",
                            flat=True,
                        )
                    ),
                )

        ledger = get_stock_ledger(
            params
        )

        # ----------------------------------------------------
        # Pagination
        # ----------------------------------------------------

        paginator = self.pagination_class()

        page = paginator.paginate_queryset(
            ledger,
            request,
        )

        serializer = StockLedgerSerializer(
            page,
            many=True,
        )

        return paginator.get_paginated_response(
            serializer.data
        )


# ============================================================
# SUPPLIER PURCHASE HISTORY
# ============================================================

class SupplierPurchaseHistoryView(APIView):

    permission_classes = [
        CanViewInventory
    ]

    pagination_class = StandardPagination

    def get(
        self,
        request,
        supplier_id,
    ):

        purchase_items = (
            get_supplier_purchase_history(
                supplier_id
            )
        )

        user = request.user

        # ----------------------------------------------------
        # Branch access protection
        # ----------------------------------------------------

        if not (
            user.is_superuser
            or user.role == "ADMIN"
        ):

            accessible_branches = (
                get_accessible_branches(user)
            )

            purchase_items = purchase_items.filter(
                purchase__branch__in=accessible_branches
            )

        # ----------------------------------------------------
        # Pagination
        # ----------------------------------------------------

        paginator = self.pagination_class()

        page = paginator.paginate_queryset(
            purchase_items,
            request,
        )

        serializer = (
            SupplierPurchaseHistorySerializer(
                page,
                many=True,
            )
        )

        return paginator.get_paginated_response(
            serializer.data
        )