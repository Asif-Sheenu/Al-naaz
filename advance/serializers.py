from rest_framework import serializers
from .models import Advance


class AdvanceSerializer(serializers.ModelSerializer):

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
        fields = "__all__"

        read_only_fields = (
            "status",
            "requested_by",
            "approved_by",
            "approved_at",
            "created_at",
        )