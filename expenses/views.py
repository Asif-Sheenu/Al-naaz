from rest_framework import status, viewsets,serializers,mixins
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from datetime import date
from .permissions import (
    CanManageFinancialAccounts,
    CanTransferMoney,
    CanSettleReceivable,
    CanCreateDailySales,
CanPostDailySales,
CanManageDeliveryPartners,
CanCreateExpense,
    CanApproveExpenseAdjustment,
    CanViewFinance,
)
from expenses.services.expense_adjustment_service import (
    request_expense_adjustment,
    approve_expense_adjustment,
    reject_expense_adjustment,
)
from .services.expense_adjustment_service import (
    request_expense_adjustment,
)
from .services.delivery_partner_service import (
    change_commission_rate,
)
from django.utils.dateparse import parse_date
from .services.report_service import get_expense_report
from .models import (
    ExpenseCategory,
    Expense,
    FinancialAccount,
    FinancialTransaction,
    DailySales,
    DailySalesPayment,
    Receivable,
    DeliveryPartner,
    DeliveryPartnerCommissionRate,
    ExpenseAdjustment,
    SupplierPayable,
    SupplierPayment,
)
from .services.receivable_settlement_service import settle_receivable
from .services.daily_sales_posting_service import post_daily_sales
from rest_framework.decorators import action
from .services.transfer_service import transfer_money
from .services.financial_account_service import (
    create_financial_account,
)
from drf_spectacular.utils import extend_schema, OpenApiParameter,OpenApiResponse
from calendar import monthrange
from .pagination import StandardPagination
from .serializers import (
    ExpenseCategorySerializer,
    ExpenseSerializer,
    ExpenseReportSerializer,
    FinancialAccountSerializer,
    TransferSerializer,
    FinancialTransactionSerializer,
    DailySalesSerializer,
    DailySalesPaymentSerializer,
    ReceivableSettlementSerializer,
    ReceivableSerializer,
    DeliveryPartnerSerializer,
    DeliveryPartnerCommissionRateSerializer,
    ChangeCommissionRateSerializer,
    ExpenseAdjustmentSerializer,
    ExpenseAdjustmentRejectSerializer,
    SupplierPaymentSerializer,
    SupplierPayableSerializer,
)
from .services.daily_sales_service import create_daily_sales
from django.db.models import Sum, Q
from notifications.services.audit_service import log_activity
from .services.expense_service import create_expense
from organization.services.access_service import (
    get_accessible_branches,
)
from expenses.services.financial_account_service import (
    get_account_balance,
)
from .services.supplier_payment_service import (
    create_supplier_payment,
)



class FinancialAccountViewSet(viewsets.ModelViewSet):

    serializer_class = FinancialAccountSerializer

    def get_permissions(self):

        if self.action in ["list", "retrieve", "balance", "transactions"]:
            permission_classes = [CanViewFinance]

        else:
            permission_classes = [CanManageFinancialAccounts]

        return [
            permission()
            for permission in permission_classes
        ]

    def get_queryset(self):

        user = self.request.user

        queryset = (
            FinancialAccount.objects
            .select_related("branch", "branch__company", "created_by")
            .order_by("branch__name", "name")
        )

        if user.is_superuser or user.role == "ADMIN":
            return queryset

        accessible_branch_ids = (
            get_accessible_branches(user)
            .values_list("id", flat=True)
        )

        queryset = queryset.filter(
            branch_id__in=accessible_branch_ids
        )

        return queryset

    def perform_create(self, serializer):

        validated_data = serializer.validated_data

        account = create_financial_account(
            branch=validated_data["branch"],
            name=validated_data["name"],
            account_type=validated_data["account_type"],
            account_purpose=validated_data["account_purpose"],
            opening_balance=validated_data["opening_balance"],
            opening_balance_date=validated_data[
                "opening_balance_date"
            ],
            created_by=self.request.user,
        )

        serializer.instance = account

    @action(
    detail=True,
    methods=["get"],
    url_path="balance",
    )
    def balance(self, request, pk=None):

        account = self.get_object()

        current_balance = get_account_balance(account)

        return Response(
            {
                "account": account.id,
                "account_name": account.name,
                "account_type": account.account_type,
                "branch": account.branch_id,
                "balance": current_balance,
            }
        )


    @action(
    detail=True,
    methods=["get"],
    url_path="transactions",
    )
    def transactions(self, request, pk=None):

        account = self.get_object()

        transactions = (
            FinancialTransaction.objects
            .filter(account=account)
            .select_related(
                "account",
                "branch",
                "created_by",
            )
            .order_by(
                "-transaction_date",
                "-id",
            )
        )

        serializer = FinancialTransactionSerializer(
            transactions,
            many=True,
        )

        return Response(
            serializer.data
        )
# =========================================================
# EXPENSE CATEGORY
# =========================================================

class ExpenseCategoryViewSet(viewsets.ModelViewSet):

    queryset = ExpenseCategory.objects.all()

    serializer_class = ExpenseCategorySerializer

    permission_classes = [
        IsAuthenticated
    ]
    pagination_class = StandardPagination

# =========================================================
# EXPENSE
# =========================================================

class ExpenseViewSet(viewsets.ModelViewSet):

    queryset = Expense.objects.select_related(
        "category",
        "created_by",
    )

    serializer_class = ExpenseSerializer

    permission_classes = [
        IsAuthenticated
    ]

    pagination_class = StandardPagination

    def perform_create(self, serializer):

        validated_data = serializer.validated_data

        expense = create_expense(
            branch=validated_data["branch"],
            category=validated_data["category"],
            payment_account=validated_data["payment_account"],
            amount=validated_data["amount"],
            expense_date=validated_data["expense_date"],
            created_by=self.request.user,
            description=validated_data.get(
                "description",
                ""
            ),
        )

        serializer.instance = expense

        # Create audit log
        log_activity(
            user=self.request.user,
            action="CREATE",
            module="EXPENSE",
            object_id=expense.id,
            description=(
                f"Created expense of ₹{expense.amount}"
            ),
            new_data={
                "category": expense.category.name,
                "amount": str(expense.amount),
                "expense_date": str(expense.expense_date),
                "description": expense.description,
            },
        )


    def perform_update(self, serializer):

        expense = self.get_object()

        # Capture old values BEFORE update
        old_data = {
            "category": expense.category.name,
            "amount": str(expense.amount),
            "expense_date": str(expense.expense_date),
            "description": expense.description,
        }

        validated_data = serializer.validated_data

        updated_expense, adjustment = update_expense(
            expense=expense,
            category=validated_data.get(
                "category",
                expense.category
            ),
            amount=validated_data.get(
                "amount",
                expense.amount
            ),
            expense_date=validated_data.get(
                "expense_date",
                expense.expense_date
            ),
            updated_by=self.request.user,
            description=validated_data.get(
                "description",
                expense.description
            ),
        )

        serializer.instance = updated_expense

        # Capture new values AFTER update
        new_data = {
            "category": updated_expense.category.name,
            "amount": str(updated_expense.amount),
            "expense_date": str(updated_expense.expense_date),
            "description": updated_expense.description,
        }

        log_activity(
            user=self.request.user,
            action="UPDATE",
            module="EXPENSE",
            object_id=updated_expense.id,
            description="Updated expense",
            old_data=old_data,
            new_data=new_data,
        )

class ExpenseReportView(APIView):

    permission_classes = [
        IsAuthenticated
    ]

    def get(self, request):

        start_date = request.query_params.get(
            "start_date"
        )

        end_date = request.query_params.get(
            "end_date"
        )

        if not start_date or not end_date:
            return Response(
                {
                    "error": (
                        "start_date and end_date "
                        "are required."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        try:

            start_date = date.fromisoformat(
                start_date
            )

            end_date = date.fromisoformat(
                end_date
            )

        except ValueError:

            return Response(
                {
                    "error": (
                        "Invalid date format. "
                        "Use YYYY-MM-DD."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        if start_date > end_date:

            return Response(
                {
                    "error": (
                        "start_date cannot be "
                        "after end_date."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        report = get_expense_report(
            start_date,
            end_date
        )

        serializer = ExpenseReportSerializer(
            report
        )

        return Response(
            serializer.data
        )    




        # monthly yearly daily ------------------------------------------------------------------------- /

@extend_schema(
    parameters=[
        OpenApiParameter(
            name="date",
            type=str,
            required=True,
            description="Report date. Format: YYYY-MM-DD",
        ),
    ]
)
class DailyExpenseReportView(APIView):

    permission_classes = [IsAuthenticated]

    def get(self, request):

        date_param = request.query_params.get("date")

        if not date_param:
            return Response(
                {
                    "error": "date is required."
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        report_date = parse_date(date_param)

        if report_date is None:
            return Response(
                {
                    "error": "Invalid date format. Use YYYY-MM-DD."
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        report = get_expense_report(
            report_date,
            report_date
        )

        serializer = ExpenseReportSerializer(report)

        return Response(serializer.data)



@extend_schema(
    parameters=[
        OpenApiParameter(
            name="month",
            type=int,
            required=True,
            description="Month number from 1 to 12.",
        ),
        OpenApiParameter(
            name="year",
            type=int,
            required=True,
            description="Four-digit year.",
        ),
    ]
)
class MonthlyExpenseReportView(APIView):

    permission_classes = [IsAuthenticated]

    def get(self, request):

        month_param = request.query_params.get("month")
        year_param = request.query_params.get("year")

        if not month_param or not year_param:
            return Response(
                {
                    "error": "month and year are required."
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            month = int(month_param)
            year = int(year_param)

        except ValueError:
            return Response(
                {
                    "error": "month and year must be valid numbers."
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        if month < 1 or month > 12:
            return Response(
                {
                    "error": "month must be between 1 and 12."
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        if year < 2000 or year > 2100:
            return Response(
                {
                    "error": "Invalid year."
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        start_date = date(
            year,
            month,
            1
        )

        last_day = monthrange(
            year,
            month
        )[1]

        end_date = date(
            year,
            month,
            last_day
        )

        report = get_expense_report(
            start_date,
            end_date
        )

        serializer = ExpenseReportSerializer(report)

        return Response(serializer.data)



@extend_schema(
    parameters=[
        OpenApiParameter(
            name="year",
            type=int,
            required=True,
            description="Four-digit year.",
        ),
    ]
)
class YearlyExpenseReportView(APIView):

    permission_classes = [IsAuthenticated]

    def get(self, request):

        year_param = request.query_params.get("year")

        if not year_param:
            return Response(
                {
                    "error": "year is required."
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            year = int(year_param)

        except ValueError:
            return Response(
                {
                    "error": "year must be a valid number."
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        if year < 2000 or year > 2100:
            return Response(
                {
                    "error": "Invalid year."
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        start_date = date(
            year,
            1,
            1
        )

        end_date = date(
            year,
            12,
            31
        )

        report = get_expense_report(
            start_date,
            end_date
        )

        serializer = ExpenseReportSerializer(report)

        return Response(serializer.data)



class TransferViewSet(viewsets.GenericViewSet):

    serializer_class = TransferSerializer
    permission_classes = [CanTransferMoney]

    def create(self, request):

        serializer = self.get_serializer(
            data=request.data
        )

        serializer.is_valid(
            raise_exception=True
        )

        data = serializer.validated_data

        from_account = data["from_account"]
        to_account = data["to_account"]

        user = request.user

        # --------------------------------------------------
        # Branch access
        # --------------------------------------------------

        if not (
            user.is_superuser
            or user.role == "ADMIN"
        ):
            if not get_accessible_branches(user).filter(
                pk=from_account.branch_id
            ).exists():
                return Response(
                    {
                        "detail": (
                            "You do not have access "
                            "to this branch."
                        )
                    },
                    status=status.HTTP_403_FORBIDDEN,
                )

        # --------------------------------------------------
        # Execute transfer
        # --------------------------------------------------

        try:

            transfer_out, transfer_in = transfer_money(
                from_account=from_account,
                to_account=to_account,
                amount=data["amount"],
                transaction_date=data["transaction_date"],
                created_by=request.user,
                idempotency_key=data.get(
                    "idempotency_key"
                ),
                description=data.get(
                    "description",
                    ""
                ),
                reference=data.get(
                    "reference",
                    ""
                ),
            )

        except ValueError as exc:

            return Response(
                {
                    "detail": str(exc)
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(
            {
                "message": (
                    "Transfer completed successfully."
                ),
                "transfer_group_id": (
                    str(
                        transfer_out.transfer_group_id
                    )
                ),
                "transfer_out_id": transfer_out.id,
                "transfer_in_id": transfer_in.id,
            },
            status=status.HTTP_201_CREATED,
        )

class FinancialTransactionViewSet(viewsets.ReadOnlyModelViewSet):

    serializer_class = FinancialTransactionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):

        user = self.request.user

        queryset = (
            FinancialTransaction.objects
            .select_related(
                "account",
                "branch",
                "created_by",
            )
            .all()
        )

        # --------------------------------------------------
        # Branch access
        # --------------------------------------------------

        if not (
            user.is_superuser
            or user.role == "ADMIN"
        ):
            queryset = queryset.filter(
                branch__in=get_accessible_branches(user)
            )

        # --------------------------------------------------
        # Filters
        # --------------------------------------------------

        branch_id = self.request.query_params.get("branch")
        account_id = self.request.query_params.get("account")
        transaction_type = self.request.query_params.get(
            "transaction_type"
        )
        direction = self.request.query_params.get("direction")

        if branch_id:
            queryset = queryset.filter(
                branch_id=branch_id
            )

        if account_id:
            queryset = queryset.filter(
                account_id=account_id
            )

        if transaction_type:
            queryset = queryset.filter(
                transaction_type=transaction_type
            )

        if direction:
            queryset = queryset.filter(
                direction=direction
            )

        return queryset



class DailySalesViewSet(viewsets.ModelViewSet):

    serializer_class = DailySalesSerializer

    def get_permissions(self):

        if self.action in [
            "list",
            "retrieve",
        ]:
            permission_classes = [
                CanViewFinance
            ]

        elif self.action == "post_sales":
            permission_classes = [
                CanPostDailySales
            ]

        else:
            permission_classes = [
                CanCreateDailySales
            ]

        return [
            permission()
            for permission in permission_classes
        ]

    def get_queryset(self):

        user = self.request.user

        queryset = (
            DailySales.objects
            .select_related(
                "branch",
                "created_by",
            )
            .prefetch_related(
                "payments",
            )
            .order_by(
                "-business_date",
                "-id",
            )
        )

        # --------------------------------------------------
        # Branch access
        # --------------------------------------------------

        if not (
            user.is_superuser
            or user.role == "ADMIN"
        ):
            queryset = queryset.filter(
                branch__in=get_accessible_branches(user)
            )

        # --------------------------------------------------
        # Optional branch filter
        # --------------------------------------------------

        branch_id = self.request.query_params.get(
            "branch"
        )

        if branch_id:
            queryset = queryset.filter(
                branch_id=branch_id
            )

        return queryset

    def perform_create(self, serializer):

        validated_data = serializer.validated_data

        daily_sales = create_daily_sales(
            branch=validated_data["branch"],
            business_date=validated_data["business_date"],
            payments=validated_data["payments"],
            created_by=self.request.user,
        )

        serializer.instance = daily_sales    



    @extend_schema(
    request=None,
    responses=DailySalesSerializer,
    )
    @action(
        detail=True,
        methods=["post"],
        url_path="post",
    )
    def post_sales(self, request, pk=None):

        daily_sales = self.get_object()

        try:
            daily_sales = post_daily_sales(
                daily_sales=daily_sales,
                created_by=request.user,
            )

        except ValueError as exc:
            return Response(
                {
                    "detail": str(exc)
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = self.get_serializer(
            daily_sales
        )

        return Response(
            {
                "message": "Daily sales posted successfully.",
                "daily_sales": serializer.data,
            },
            status=status.HTTP_200_OK,
        )    

    def perform_destroy(self, instance):

        if instance.status == DailySales.Status.POSTED:
            raise serializers.ValidationError(
                "Posted daily sales cannot be deleted."
            )

        instance.delete()




class ReceivableViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = ReceivableSerializer
    permission_classes = [CanViewFinance]

    def get_queryset(self):
        user = self.request.user

        queryset = (
            Receivable.objects
            .select_related(
                "branch",
                "receivable_account",
                "daily_sales_payment",
                "daily_sales_payment__daily_sales",
                "created_by",
            )
            .order_by(
                "-business_date",
                "-id",
            )
        )

        # ADMIN / superuser → all branches
        if user.is_superuser or user.role == "ADMIN":
            return queryset

        # Other users → only accessible branches
        accessible_branch_ids = (
            get_accessible_branches(user)
            .values_list("id", flat=True)
        )

        queryset = queryset.filter(
            branch_id__in=accessible_branch_ids
        )

        # Optional status filter
        status_filter = self.request.query_params.get("status")

        if status_filter:
            queryset = queryset.filter(
                status=status_filter
            )

        return queryset




class ReceivableSettlementViewSet(viewsets.ViewSet):
    permission_classes = [CanSettleReceivable]

    @extend_schema(
        request=ReceivableSettlementSerializer,
        responses={
            201: OpenApiResponse(
                description="Receivable settled successfully."
            ),
        },
    )
    def create(self, request):

        serializer = ReceivableSettlementSerializer(
            data=request.data,
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)

        data = serializer.validated_data

        receivable = data["receivable"]
        destination_account = data["destination_account"]

        user = request.user

        # Branch access check
        if not (
            user.is_superuser
            or user.role == "ADMIN"
        ):
            accessible_branches = get_accessible_branches(user)

            if not accessible_branches.filter(
                pk=receivable.branch_id
            ).exists():
                return Response(
                    {
                        "detail": (
                            "You do not have access "
                            "to this branch."
                        )
                    },
                    status=status.HTTP_403_FORBIDDEN,
                )

            if not accessible_branches.filter(
                pk=destination_account.branch_id
            ).exists():
                return Response(
                    {
                        "detail": (
                            "You do not have access "
                            "to the destination branch."
                        )
                    },
                    status=status.HTTP_403_FORBIDDEN,
                )

        try:

            settlement = settle_receivable(
                receivable=receivable,
                destination_account=destination_account,
                gross_amount=data["gross_amount"],
                settlement_date=data["settlement_date"],
                created_by=user,
                reference=data.get("reference", ""),
                description=data.get("description", ""),
            )

        except ValueError as exc:

            return Response(
                {"detail": str(exc)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(
            {
                "message": "Receivable settled successfully.",
                "settlement_id": settlement.id,
                "receivable_id": settlement.receivable_id,
                "gross_amount": str(
                    settlement.gross_amount
                ),
                "commission_amount": str(
                    settlement.commission_amount
                ),
                "received_amount": str(
                    settlement.received_amount
                ),
                "destination_account": (
                    settlement.destination_account_id
                ),
                "settlement_date": (
                    settlement.settlement_date
                ),
            },
            status=status.HTTP_201_CREATED,
        )

class DeliveryPartnerViewSet(viewsets.ModelViewSet):

    serializer_class = DeliveryPartnerSerializer
    permission_classes = [CanManageDeliveryPartners]

    def get_queryset(self):

        user = self.request.user

        queryset = DeliveryPartner.objects.select_related(
            "branch",
            "created_by",
        )

        if user.is_superuser or user.role == "ADMIN":
            return queryset

        accessible_branches = get_accessible_branches(user)

        return queryset.filter(
            branch__in=accessible_branches
        )

    def perform_create(self, serializer):

        serializer.save(
            created_by=self.request.user
        )

    @extend_schema(
    request=ChangeCommissionRateSerializer,
    responses={201: ChangeCommissionRateSerializer},
    )
    @action(
        detail=True,
        methods=["post"],
        url_path="change-commission-rate",
    )
    def change_commission_rate(self, request, pk=None):

        delivery_partner = self.get_object()

        serializer = ChangeCommissionRateSerializer(
            data=request.data
        )

        serializer.is_valid(raise_exception=True)

        try:
            rate = change_commission_rate(
                delivery_partner=delivery_partner,
                commission_rate=serializer.validated_data[
                    "commission_rate"
                ],
                effective_from=serializer.validated_data[
                    "effective_from"
                ],
                created_by=request.user,
            )

        except ValueError as exc:

            return Response(
                {"detail": str(exc)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(
            {
                "message": "Commission rate changed successfully.",
                "delivery_partner": rate.delivery_partner_id,
                "commission_rate": str(rate.commission_rate),
                "effective_from": rate.effective_from,
                "effective_to": rate.effective_to,
            },
            status=status.HTTP_201_CREATED,
        )        




class DeliveryPartnerCommissionRateViewSet(viewsets.ModelViewSet):

    serializer_class = DeliveryPartnerCommissionRateSerializer
    permission_classes = [CanManageDeliveryPartners]

    def get_queryset(self):

        user = self.request.user

        queryset = DeliveryPartnerCommissionRate.objects.select_related(
            "delivery_partner",
            "delivery_partner__branch",
            "created_by",
        )

        if user.is_superuser or user.role == "ADMIN":
            return queryset

        accessible_branches = get_accessible_branches(user)

        return queryset.filter(
            delivery_partner__branch__in=accessible_branches
        )

    def perform_create(self, serializer):

        serializer.save(
            created_by=self.request.user
        )            
class ExpenseAdjustmentViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.CreateModelMixin,
    viewsets.GenericViewSet,
):

    serializer_class = ExpenseAdjustmentSerializer
    pagination_class = StandardPagination
    queryset = ExpenseAdjustment.objects.all()

    def get_permissions(self):

        if self.action == "create":
            permission_classes = [CanCreateExpense]

        elif self.action in ["approve", "reject"]:
            permission_classes = [CanApproveExpenseAdjustment]

        else:
            permission_classes = [CanViewFinance]

        return [
            permission()
            for permission in permission_classes
        ]

    def get_queryset(self):

        user = self.request.user

        queryset = (
            ExpenseAdjustment.objects
            .select_related(
                "expense",
                "expense__branch",
                "expense__category",
                "expense__payment_account",
                "requested_by",
                "approved_by",
                "old_payment_account",
                "new_payment_account",
                "old_category",
                "new_category",
            )
            .order_by(
                "-requested_at",
                "-id",
            )
        )

        # ---------------------------------------------
        # ADMIN / SUPERUSER
        # ---------------------------------------------

        if user.is_superuser or user.role == "ADMIN":
            return queryset

        # ---------------------------------------------
        # BRANCH ISOLATION
        # ---------------------------------------------

        return queryset.filter(
            expense__branch__in=get_accessible_branches(user)
        )

    # =================================================
    # REQUEST ADJUSTMENT
    # =================================================

    def perform_create(self, serializer):

        data = serializer.validated_data

        expense = data["expense"]

        try:

            adjustment = request_expense_adjustment(
                expense=expense,
                new_amount=data["new_amount"],
                new_payment_account=data[
                    "new_payment_account"
                ],
                new_expense_date=data[
                    "new_expense_date"
                ],
                new_category=data["new_category"],
                new_description=data.get(
                    "new_description",
                    "",
                ),
                reason=data["reason"],
                requested_by=self.request.user,
            )

        except ValueError as exc:

            raise serializers.ValidationError(
                {"detail": str(exc)}
            )

        serializer.instance = adjustment

    # =================================================
    # APPROVE
    # =================================================
    @extend_schema(
    request=None,
    responses=ExpenseAdjustmentSerializer,
    )
    @action(
        detail=True,
        methods=["post"],
        url_path="approve",
    )
    def approve(self, request, pk=None):

        adjustment = self.get_object()

        try:

            adjustment = approve_expense_adjustment(
                adjustment=adjustment,
                approved_by=request.user,
            )

        except ValueError as exc:

            raise serializers.ValidationError(
                {"detail": str(exc)}
            )

        serializer = self.get_serializer(adjustment)

        return Response(
            serializer.data,
            status=status.HTTP_200_OK,
        )

    # =================================================
    # REJECT
    # =================================================

    @extend_schema(
    request=ExpenseAdjustmentRejectSerializer,
    responses=ExpenseAdjustmentSerializer,
    )
    @action(
    detail=True,
    methods=["post"],
    url_path="reject",
    )
    def reject(self, request, pk=None):

        adjustment = self.get_object()

        rejection_reason = request.data.get(
            "rejection_reason"
        )

        try:

            adjustment = reject_expense_adjustment(
                adjustment=adjustment,
                rejected_by=request.user,
                rejection_reason=rejection_reason,
            )

        except ValueError as exc:

            raise serializers.ValidationError(
                {"detail": str(exc)}
            )

        serializer = self.get_serializer(adjustment)

        return Response(
            serializer.data,
            status=status.HTTP_200_OK,
        )


class SupplierPaymentViewSet(viewsets.ModelViewSet):

    serializer_class = SupplierPaymentSerializer
    pagination_class = StandardPagination

    def get_permissions(self):

        if self.action in ["list", "retrieve"]:
            permission_classes = [CanViewFinance]

        else:
            permission_classes = [CanCreateExpense]

        return [
            permission()
            for permission in permission_classes
        ]

    def get_queryset(self):

        user = self.request.user

        queryset = (
            SupplierPayment.objects
            .select_related(
                "payable",
                "payable__supplier",
                "payable__branch",
                "payment_account",
                "created_by",
            )
            .order_by("-payment_date", "-id")
        )

        if user.is_superuser or user.role == "ADMIN":
            return queryset

        accessible_branch_ids = (
            get_accessible_branches(user)
            .values_list("id", flat=True)
        )

        return queryset.filter(
            payable__branch_id__in=accessible_branch_ids
        )

    def perform_create(self, serializer):

        validated_data = serializer.validated_data

        payable = validated_data["payable"]

        payment = create_supplier_payment(
            payable=payable,
            amount=validated_data["amount"],
            payment_account=validated_data["payment_account"],
            payment_date=validated_data["payment_date"],
            created_by=self.request.user,
            reference=validated_data.get("reference", ""),
            remarks=validated_data.get("remarks", ""),
        )

        serializer.instance = payment    


class SupplierPayableViewSet(
    viewsets.ReadOnlyModelViewSet
):

    serializer_class = SupplierPayableSerializer

    permission_classes = [
        CanViewFinance
    ]

    pagination_class = StandardPagination

    def get_queryset(self):

        user = self.request.user

        queryset = (
            SupplierPayable.objects
            .select_related(
                "purchase",
                "supplier",
                "branch",
            )
            .prefetch_related(
                "payments",
                "payments__payment_account",
                "payments__created_by",
            )
            .order_by(
                "-created_at",
                "-id",
            )
        )

        # ---------------------------------------------
        # ADMIN / SUPERUSER → ALL BRANCHES
        # ---------------------------------------------

        if not (
            user.is_superuser
            or user.role == "ADMIN"
        ):
            queryset = queryset.filter(
                branch__in=get_accessible_branches(user)
            )

        # ---------------------------------------------
        # OPTIONAL BRANCH FILTER
        # ---------------------------------------------

        branch_id = self.request.query_params.get(
            "branch"
        )

        if branch_id:
            queryset = queryset.filter(
                branch_id=branch_id
            )

        # ---------------------------------------------
        # OPTIONAL SUPPLIER FILTER
        # ---------------------------------------------

        supplier_id = self.request.query_params.get(
            "supplier"
        )

        if supplier_id:
            queryset = queryset.filter(
                supplier_id=supplier_id
            )

        # ---------------------------------------------
        # OPTIONAL STATUS FILTER
        # ---------------------------------------------

        payable_status = self.request.query_params.get(
            "status"
        )

        if payable_status:
            queryset = queryset.filter(
                status=payable_status
            )

        return queryset        