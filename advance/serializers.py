from rest_framework import serializers
from .models import Advance
from organization.services.access_service import (
    get_accessible_branches,
)

class AdvanceSerializer(serializers.ModelSerializer):

    branch_name = serializers.CharField(source="employee.branch.name",read_only =True)

    employee_name = serializers.CharField(
        source="employee.name",
        read_only=True
    )

    requested_by_name = serializers.CharField(
        source="requested_by.username",
        read_only=True
    )

    approved_by_name = serializers.CharField(
        source="approved_by.username",
        read_only=True
    )

    class Meta:
        model = Advance

        fields = [
            "id",
            "employee",
            "employee_name",
            "amount",
            "date",
            "reason",
            "remarks",
            "branch_name",
            "status",
            "requested_by",
            "requested_by_name",
            "approved_by",
            "approved_by_name",
            "approved_at",
            "created_at",
        ]

        read_only_fields = [
            "id",
            "status",
            "branch_name",
            "requested_by",
            "requested_by_name",
            "approved_by",
            "approved_by_name",
            "approved_at",
            "created_at",
        ]

    def validate_amount(self, value):
        if value <= 0:
            raise serializers.ValidationError(
                "Advance amount must be greater than zero."
            )
        return value    


    def validate_employee(self, employee):
        request = self.context.get("request")

        if not request:
            return employee

        user = request.user

        if user.is_superuser or user.role == "ADMIN":
            return employee

        if not get_accessible_branches(user).filter(
            pk=employee.branch_id
        ).exists():
            raise serializers.ValidationError(
                "You do not have access to this employee's branch."
            )

        return employee