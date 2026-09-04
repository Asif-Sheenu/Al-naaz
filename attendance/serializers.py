from rest_framework import serializers

from organization.services.access_service import (
    get_accessible_branches,
)

from .models import Attendance


class AttendanceSerializer(serializers.ModelSerializer):

    employee_name = serializers.CharField(
        source="employee.name",
        read_only=True
    )

    class Meta:
        model = Attendance

        fields = [
            "id",
            "employee",
            "employee_name",
            "date",
            "status",
            "is_paid",
            "remarks",
            "created_at",
        ]

        read_only_fields = [
            "id",
            "employee_name",
            "created_at",
        ]

    def validate_employee(self, employee):

        request = self.context.get("request")

        if not request:
            return employee

        user = request.user

        # Admin / superuser can manage employees
        # from all active branches.
        if (
            user.is_superuser
            or user.role == "ADMIN"
        ):
            return employee

        accessible_branch_ids = (
            get_accessible_branches(user)
            .values_list(
                "id",
                flat=True,
            )
        )

        if employee.branch_id not in accessible_branch_ids:
            raise serializers.ValidationError(
                "You do not have access to this employee's branch."
            )

        return employee


class DailyAttendanceSerializer(serializers.Serializer):

    employee = serializers.IntegerField()

    employee_name = serializers.CharField()

    designation = serializers.CharField()

    status = serializers.ChoiceField(
        choices=Attendance.Status.choices,
        allow_null=True,
    )

    is_paid = serializers.BooleanField()


    remarks = serializers.CharField(
        allow_blank=True
    )        



class BulkAttendanceRecordSerializer(serializers.Serializer):

    employee = serializers.IntegerField()

    status = serializers.ChoiceField(
        choices=Attendance.Status.choices
    )

    is_paid = serializers.BooleanField(
        required=False,
        default=True,
    )

    remarks = serializers.CharField(
        required=False,
        allow_blank=True,
        default=""
    )


class BulkAttendanceSerializer(serializers.Serializer):

    branch = serializers.IntegerField()

    date = serializers.DateField()

    records = BulkAttendanceRecordSerializer(
        many=True
    )