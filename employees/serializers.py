from rest_framework import serializers

from organization.services.access_service import (
    get_accessible_branches,
)

from .models import Employee, EmployeeIdentityProof


class EmployeeSerializer(serializers.ModelSerializer):

    class Meta:
        model = Employee

        fields = [
            "id",
            "branch",
            "name",
            "phone",
            "address",
            "designation",
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