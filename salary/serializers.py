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

    month = serializers.IntegerField(min_value=1, max_value=12)

    year = serializers.IntegerField(min_value=2000)        




# salary dashboard  serializer ------------------------------------------------

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