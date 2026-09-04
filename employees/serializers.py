from rest_framework import serializers
from django.db import transaction
from organization.services.access_service import (
    get_accessible_branches,
)
from .models import EmployeeSalaryHistory
from .models import Employee, EmployeeIdentityProof
from .services.salary_validation import validate_salary_data
from datetime import date


class EmployeeSerializer(serializers.ModelSerializer):

    branch_name = serializers.CharField(
        source="branch.name",
        read_only=True,
    )

    department_name = serializers.CharField(
    source="department.name",
    read_only=True,
    )
    class Meta:
        model = Employee


        fields = [
            "id",
            "branch",
            "branch_name", 
            "name",
            "phone",
            "address",
            "designation",
            "department",
            "department_name",
            "salary_type",
            "biweekly_salary",
            "monthly_salary",
            "daily_wage",
            "joining_date",
            "is_active",
            "created_at",
            "updated_at",
        ]

        read_only_fields = [
            "id",
            "branch_name",
            "department_name",
            "created_at",
            "updated_at",
        ]

    def validate_branch(self, branch):

        request = self.context.get("request")

        if not request:
            return branch

        user = request.user

        if (
            user.is_superuser
            or user.role == "ADMIN"
        ):
            return branch

        if not get_accessible_branches(user).filter(
            pk=branch.pk
        ).exists():

            raise serializers.ValidationError(
                "You do not have access to this branch."
            )

        return branch

    @transaction.atomic
    def create(self, validated_data):

        request = self.context.get("request")

        employee = Employee.objects.create(
            **validated_data
        )

        EmployeeSalaryHistory.objects.create(
            employee=employee,
            salary_type=employee.salary_type,
            monthly_salary=employee.monthly_salary,
            daily_wage=employee.daily_wage,
            biweekly_salary=employee.biweekly_salary,
            effective_from=employee.joining_date,
            reason="Initial salary",
            created_by=request.user,
        )

        return employee
    
    def validate(self, attrs):

        branch = attrs.get(
            "branch",
            self.instance.branch if self.instance else None
        )

        department = attrs.get(
            "department",
            self.instance.department if self.instance else None
        )

        # Department must belong to the selected employee branch
        if department and branch:
            if department.branch_id != branch.id:
                raise serializers.ValidationError({
                    "department": (
                        "Department must belong to the selected branch."
                    )
                })

        # Salary validation
        validate_salary_data(
            salary_type=attrs.get(
                "salary_type",
                self.instance.salary_type if self.instance else None
            ),
            monthly_salary=attrs.get(
                "monthly_salary",
                self.instance.monthly_salary if self.instance else None
            ),
            daily_wage=attrs.get(
                "daily_wage",
                self.instance.daily_wage if self.instance else None
            ),
            biweekly_salary=attrs.get(
                "biweekly_salary",
                self.instance.biweekly_salary if self.instance else None
            ),
        )

        return attrs

class EmployeeIdentityProofSerializer(
    serializers.ModelSerializer
):

    masked_document_number = serializers.SerializerMethodField()

    class Meta:
        model = EmployeeIdentityProof

        fields = [
            "id",
            "employee",
            "document_type",
            "masked_document_number",
            "original_filename",
            "mime_type",
            "file_size",
            "uploaded_by",
            "created_at",
            "updated_at",
        ]

        read_only_fields = [
            "id",
            "employee",
            "masked_document_number",
            "original_filename",
            "mime_type",
            "file_size",
            "uploaded_by",
            "created_at",
            "updated_at",
        ]

    def get_masked_document_number(self, obj):

        document_number = obj.document_number

        if not document_number:
            return None

        if len(document_number) <= 4:
            return "*" * len(document_number)

        return (
            "*" * (len(document_number) - 4)
            + document_number[-4:]
        )

class EmployeeIdentityProofUploadSerializer(
    serializers.Serializer
):

    document_type = serializers.ChoiceField(
        choices=EmployeeIdentityProof.DocumentType.choices
    )

    document_number = serializers.CharField(
        max_length=100
    )

    file = serializers.FileField(
        help_text="Identity proof file (PDF, JPEG, or PNG)."
    )


class EmployeeSalaryHistorySerializer(serializers.ModelSerializer):

    employee_name = serializers.CharField(
        source="employee.name",
        read_only=True,
    )

    created_by_name = serializers.CharField(
        source="created_by.username",
        read_only=True,
    )

    class Meta:
        model = EmployeeSalaryHistory

        fields = [
            "id",
            "employee",
            "employee_name",
            "salary_type",
            "monthly_salary",
            "daily_wage",
            "biweekly_salary",
            "effective_from",
            "effective_to",
            "reason",
            "created_by",
            "created_by_name",
            "created_at",
        ]

        read_only_fields = [
            "id",
            "employee",
            "employee_name",
            "effective_to",
            "created_by",
            "created_by_name",
            "created_at",
        ]

    

    def validate(self, attrs):

        validate_salary_data(
            salary_type=attrs.get("salary_type"),
            monthly_salary=attrs.get("monthly_salary"),
            daily_wage=attrs.get("daily_wage"),
            biweekly_salary=attrs.get("biweekly_salary"),
        )

        effective_from = attrs.get("effective_from")

        if effective_from and effective_from.day != 1:
            raise serializers.ValidationError({
                "effective_from": (
                    "Salary revisions must be effective "
                    "from the first day of a month."
                )
            })

        return attrs