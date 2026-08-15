from rest_framework import serializers

from .models import (
    ExpenseCategory,
    Expense,
    PettyCashLedger,
)


class ExpenseCategorySerializer(serializers.ModelSerializer):

    class Meta:
        model = ExpenseCategory

        fields = [
            "id",
            "name",
            "is_active",
            "created_at",
        ]

        read_only_fields = [
            "id",
            "created_at",
        ]


class ExpenseSerializer(serializers.ModelSerializer):

    category_name = serializers.CharField(
        source="category.name",
        read_only=True
    )

    created_by_name = serializers.CharField(
        source="created_by.username",
        read_only=True
    )

    class Meta:
        model = Expense

        fields = [
            "id",
            "category",
            "category_name",
            "amount",
            "expense_date",
            "description",
            "created_by",
            "created_by_name",
            "created_at",
            "updated_at",
        ]

        read_only_fields = [
            "id",
            "created_by",
            "created_by_name",
            "created_at",
            "updated_at",
        ]

    def validate_amount(self, value):

        if value <= 0:
            raise serializers.ValidationError(
                "Expense amount must be greater than zero."
            )

        return value

    def validate_category(self, value):

        if not value.is_active:
            raise serializers.ValidationError(
                "This expense category is inactive."
            )

        return value


class PettyCashLedgerSerializer(serializers.ModelSerializer):

    created_by_name = serializers.CharField(
        source="created_by.username",
        read_only=True
    )

    expense_id = serializers.IntegerField(
        source="expense.id",
        read_only=True
    )

    class Meta:
        model = PettyCashLedger

        fields = [
            "id",
            "transaction_type",
            "amount",
            "balance_after",
            "transaction_date",
            "expense_id",
            "remarks",
            "created_by",
            "created_by_name",
            "created_at",
        ]

        read_only_fields = [
            "id",
            "balance_after",
            "expense_id",
            "created_by",
            "created_by_name",
            "created_at",
        ]


class AddPettyCashSerializer(serializers.Serializer):

    amount = serializers.DecimalField(
        max_digits=12,
        decimal_places=2
    )

    transaction_date = serializers.DateField()

    remarks = serializers.CharField(
        required=False,
        allow_blank=True
    )

    def validate_amount(self, value):

        if value <= 0:
            raise serializers.ValidationError(
                "Amount must be greater than zero."
            )

        return value        

    # reposrt service =--------------------------------------------------------------------------------- 


class ExpenseReportSerializer(serializers.Serializer):

    start_date = serializers.DateField()

    end_date = serializers.DateField()

    opening_balance = serializers.DecimalField(
        max_digits=12,
        decimal_places=2
    )

    total_cash_added = serializers.DecimalField(
        max_digits=12,
        decimal_places=2
    )

    total_expense = serializers.DecimalField(
        max_digits=12,
        decimal_places=2
    )

    expense_count = serializers.IntegerField()

    closing_balance = serializers.DecimalField(
        max_digits=12,
        decimal_places=2
    )

    category_totals = serializers.ListField()