from rest_framework import status, viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from datetime import date
from django.utils.dateparse import parse_date
from .services.report_service import get_expense_report
from .models import (
    ExpenseCategory,
    Expense,
    PettyCashLedger,
)
from drf_spectacular.utils import extend_schema, OpenApiParameter
from calendar import monthrange
from .pagination import StandardPagination
from .serializers import (
    ExpenseCategorySerializer,
    ExpenseSerializer,
    PettyCashLedgerSerializer,
    AddPettyCashSerializer,
    ExpenseReportSerializer
)
from notifications.services.audit_service import log_activity
from .services.petty_cash_service import (
    add_cash,
    create_expense,
    update_expense
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
            category=validated_data["category"],
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
# =========================================================
# PETTY CASH LEDGER
# =========================================================

class PettyCashLedgerView(APIView):

    permission_classes = [IsAuthenticated]

    pagination_class = StandardPagination

    def get(self, request):

        ledger = (
            PettyCashLedger.objects
            .select_related(
                "expense",
                "created_by",
            )
            .order_by("-id")
        )

        paginator = self.pagination_class()

        page = paginator.paginate_queryset(
            ledger,
            request
        )

        serializer = PettyCashLedgerSerializer(
            page,
            many=True
        )

        return paginator.get_paginated_response(
            serializer.data
        )


# =========================================================
# ADD PETTY CASH
# =========================================================

class AddPettyCashView(APIView):

    permission_classes = [
        IsAuthenticated
    ]
    @extend_schema(
        request=AddPettyCashSerializer,
        responses=PettyCashLedgerSerializer
    )
    def post(self, request):

        serializer = AddPettyCashSerializer(
            data=request.data
        )

        serializer.is_valid(
            raise_exception=True
        )

        transaction = add_cash(
            amount=serializer.validated_data["amount"],
            transaction_date=serializer.validated_data["transaction_date"],
            created_by=request.user,
            remarks=serializer.validated_data.get(
                "remarks",
                ""
            ),
        )

        # Create audit log
        log_activity(
            user=request.user,
            action="CREATE",
            module="PETTY_CASH",
            object_id=transaction.id,
            description=(
                f"Added ₹{transaction.amount} "
                f"to petty cash"
            ),
            new_data={
                "transaction_type": transaction.transaction_type,
                "amount": str(transaction.amount),
                "transaction_date": str(
                    transaction.transaction_date
                ),
                "balance_after": str(
                    transaction.balance_after
                ),
                "remarks": transaction.remarks,
            },
        )

        response_serializer = PettyCashLedgerSerializer(
            transaction
        )

        return Response(
            response_serializer.data,
            status=status.HTTP_201_CREATED
        )


# =========================================================
# CURRENT PETTY CASH BALANCE
# =========================================================

class PettyCashBalanceView(APIView):

    permission_classes = [
        IsAuthenticated
    ]

    def get(self, request):

        last_entry = (
            PettyCashLedger.objects
            .order_by("-id")
            .first()
        )

        balance = (
            last_entry.balance_after
            if last_entry
            else 0
        )

        return Response({
            "current_balance": balance
        })



    # report service ---------------------------------------------------------------------------------------  

@extend_schema(
    parameters=[
        OpenApiParameter(
            name="start_date",
            type=str,
            required=True,
            description="Report start date. Format: YYYY-MM-DD",
        ),
        OpenApiParameter(
            name="end_date",
            type=str,
            required=True,
            description="Report end date. Format: YYYY-MM-DD",
        ),
    ]
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