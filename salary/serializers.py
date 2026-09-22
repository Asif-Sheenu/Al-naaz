from rest_framework import serializers
from .models import Salary


class SalarySerializer(serializers.ModelSerializer):

    employee_name = serializers.CharField(
        source="employee.name",
        read_only=True
    )

    class Meta:
        model = Salary
        fields = "__all__"


class SalaryGenerateSerializer(serializers.Serializer):

    employee = serializers.IntegerField(
        min_value=1
    )

    month = serializers.IntegerField(
        min_value=1,
        max_value=12
    )

    year = serializers.IntegerField(
        min_value=2000
    )


# ------------------------------------------------
# Salary Dashboard Serializer
# ------------------------------------------------

class PayrollDashboardSerializer(serializers.Serializer):

    total_employees = serializers.IntegerField()

    active_employees = serializers.IntegerField()

    paid_salaries = serializers.IntegerField()

    pending_salaries = serializers.IntegerField()

    employees_with_approved_advance = serializers.IntegerField()

    pending_advance_requests = serializers.IntegerField()

    approved_advances = serializers.IntegerField()

    total_payroll = serializers.DecimalField(
        max_digits=12,
        decimal_places=2
    )

    total_advance = serializers.DecimalField(
        max_digits=12,
        decimal_places=2
    )

    total_net_salary = serializers.DecimalField(
        max_digits=12,
        decimal_places=2
    )

    month = serializers.IntegerField()

    year = serializers.IntegerField()


# ------------------------------------------------
# Generate All Serializer
# ------------------------------------------------

class SalaryGenerateAllSerializer(serializers.Serializer):

    month = serializers.IntegerField(
        min_value=1,
        max_value=12
    )

    year = serializers.IntegerField(
        min_value=2000
    )


# ------------------------------------------------
# Individual Generated Salary Response
# ------------------------------------------------

class SalaryGenerateResultSerializer(serializers.Serializer):

    salary_id = serializers.IntegerField()

    employee_id = serializers.IntegerField()

    employee_name = serializers.CharField()

    month = serializers.IntegerField()

    year = serializers.IntegerField()

    salary_type = serializers.CharField()

    working_days = serializers.IntegerField()

    present_days = serializers.IntegerField()

    absent_days = serializers.IntegerField()

    leave_days = serializers.IntegerField()

    half_days = serializers.IntegerField()

    gross_salary = serializers.DecimalField(
        max_digits=10,
        decimal_places=2
    )

    attendance_deduction = serializers.DecimalField(
        max_digits=10,
        decimal_places=2
    )

    advance_deduction = serializers.DecimalField(
        max_digits=10,
        decimal_places=2
    )

    other_deduction = serializers.DecimalField(
        max_digits=10,
        decimal_places=2
    )

    net_salary = serializers.DecimalField(
        max_digits=10,
        decimal_places=2
    )

    status = serializers.CharField()

    payment_date = serializers.DateField(
        allow_null=True
    )

    remarks = serializers.CharField()

    created_at = serializers.DateTimeField()


# ------------------------------------------------
# Generate All Response
# ------------------------------------------------

class SalaryGenerateAllResponseSerializer(serializers.Serializer):

    employees_processed = serializers.IntegerField()

    generated_count = serializers.IntegerField()

    skipped_count = serializers.IntegerField()

    failed_count = serializers.IntegerField()

    generated = SalaryGenerateResultSerializer(
        many=True
    )

    skipped = serializers.ListField()

    failed = serializers.ListField()