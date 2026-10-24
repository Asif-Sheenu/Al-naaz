from rest_framework import serializers

from .models import IssuedItem, ClearancePayment



class ClearancePaymentSerializer(serializers.ModelSerializer):
    recorded_by_name = serializers.CharField(
        source="recorded_by.username",
        read_only=True,
    )

    class Meta:
        model = ClearancePayment
        fields = [
            "id",
            "issued_item",
            "amount",
            "payment_method",
            "payment_date",
            "recorded_by",
            "recorded_by_name",
            "reference",
            "notes",
            "created_at",
        ]
        read_only_fields = [
            "id",
            "recorded_by",
            "recorded_by_name",
            "created_at",
        ]


class IssuedItemSerializer(serializers.ModelSerializer):
    employee_name = serializers.CharField(
        source="employee.name",
        read_only=True,
    )

    issued_by_name = serializers.CharField(
        source="issued_by.username",
        read_only=True,
    )

    manager_approved_by_name = serializers.CharField(
        source="manager_approved_by.username",
        read_only=True,
        allow_null=True,
    )

    admin_approved_by_name = serializers.CharField(
        source="admin_approved_by.username",
        read_only=True,
        allow_null=True,
    )

    payments = ClearancePaymentSerializer(
        many=True,
        read_only=True,
    )

    total_paid = serializers.SerializerMethodField()
    outstanding_balance = serializers.SerializerMethodField()

    class Meta:
        model = IssuedItem
        fields = [
            "id",
            "employee",
            "employee_name",
            "item_name",
            "quantity",
            "unit_value",
            "employee_payable",
            "issued_date",
            "issued_by",
            "issued_by_name",
            "approval_status",
            "manager_approved_by",
            "manager_approved_by_name",
            "manager_approved_at",
            "admin_approved_by",
            "admin_approved_by_name",
            "admin_approved_at",
            "rejection_reason",
            "notes",
            "payments",
            "total_paid",
            "outstanding_balance",
            "created_at",
            "updated_at",
        ]

        read_only_fields = [
            "id",
            "issued_by",
            "approval_status",
            "manager_approved_by",
            "manager_approved_at",
            "admin_approved_by",
            "admin_approved_at",
            "rejection_reason",
            "created_at",
            "updated_at",
        ]

    def get_total_paid(self, obj):
        from django.db.models import Sum

        from .services import ZERO

        total = (
            obj.payments.aggregate(total=Sum("amount"))["total"]
            or ZERO
        )

        return total

    def get_outstanding_balance(self, obj):
        from .services import get_clearance_balance

        return get_clearance_balance(obj)






class ClearanceRejectionSerializer(serializers.Serializer):
    rejection_reason = serializers.CharField(
        required=True,
        allow_blank=False,
        trim_whitespace=True,
    )

    stage = serializers.ChoiceField(
        choices=[
            ("MANAGER", "Manager"),
            ("ADMIN", "Admin"),
        ],
        required=True,
    )    