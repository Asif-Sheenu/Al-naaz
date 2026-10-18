import logging

from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema, OpenApiTypes

from organization.services.access_service import get_accessible_branches
from notifications.services.notification_service import notify_admins_and_managers

from .models import Employee, EmployeeIdentityProof
from .permissions import CanManageEmployees, CanManageEmployeeSalary
from .serializers import (
    EmployeeSerializer,
    EmployeeIdentityProofSerializer,
    EmployeeIdentityProofUploadSerializer,
    EmployeeSalaryHistorySerializer,
)
from .services import create_salary_revision
from .services.identity_proof_service import (
    create_identity_proof,
    get_identity_proof_file_url,
)

logger = logging.getLogger(__name__)


def send_employee_notification(
    *,
    employee,
    title,
    message,
    notification_type="INFO",
):
    """Create notifications for admins/managers; never break the employee action."""
    try:
        notify_admins_and_managers(
            notification_type=notification_type,
            title=title,
            message=message,
            module="EMPLOYEES",
            object_id=employee.pk,
            branch=employee.branch,
        )
    except Exception:
        logger.exception(
            "Employee notification failed for employee %s",
            employee.pk,
        )


class EmployeeViewSet(viewsets.ModelViewSet):
    serializer_class = EmployeeSerializer
    permission_classes = [CanManageEmployees]

    def get_queryset(self):
        user = self.request.user

        queryset = (
            Employee.objects
            .select_related("branch", "department")
            .order_by("-id")
        )

        # Preserve branch-level access restrictions.
        if not (user.is_superuser or user.role == "ADMIN"):
            accessible_branch_ids = (
                get_accessible_branches(user).values_list("id", flat=True)
            )
            queryset = queryset.filter(branch_id__in=accessible_branch_ids)

        # Optional query filters.
        branch_id = self.request.query_params.get("branch")
        if branch_id:
            queryset = queryset.filter(branch_id=branch_id)

        department_id = self.request.query_params.get("department")
        if department_id:
            queryset = queryset.filter(department_id=department_id)

        designation = self.request.query_params.get("designation")
        if designation:
            queryset = queryset.filter(designation__iexact=designation)

        is_active = self.request.query_params.get("is_active")
        if is_active is not None:
            is_active = is_active.lower() == "true"
            queryset = queryset.filter(is_active=is_active)

        return queryset

    def perform_create(self, serializer):
        employee = serializer.save()
        send_employee_notification(
            employee=employee,
            title="New Employee Added",
            message=(
                f"Employee {employee} has been added "
                f"to {employee.branch.name}."
            ),
        )

    def perform_update(self, serializer):
        employee = serializer.save()
        send_employee_notification(
            employee=employee,
            title="Employee Details Updated",
            message=(
                f"Employee {employee} details have been "
                f"updated in {employee.branch.name}."
            ),
        )

    def perform_destroy(self, instance):
        employee_name = str(instance)
        branch = instance.branch
        employee_id = instance.pk

        instance.delete()

        try:
            notify_admins_and_managers(
                notification_type="WARNING",
                title="Employee Deleted",
                message=(
                    f"Employee {employee_name} (ID: {employee_id}) "
                    f"was deleted from {branch.name}."
                ),
                module="EMPLOYEES",
                object_id=employee_id,
                branch=branch,
            )
        except Exception:
            logger.exception(
                "Employee deletion notification failed for employee %s",
                employee_id,
            )

    @extend_schema(
        request=EmployeeIdentityProofUploadSerializer,
        responses=EmployeeIdentityProofSerializer,
    )
    @action(
        detail=True,
        methods=["get", "post"],
        url_path="identity-proof",
        parser_classes=[MultiPartParser, FormParser],
    )
    def identity_proof(self, request, pk=None):
        employee = self.get_object()
        self.check_object_permissions(request, employee)

        if request.method == "GET":
            try:
                identity_proof = employee.identity_proof
            except EmployeeIdentityProof.DoesNotExist:
                return Response(
                    {"detail": "Identity proof not found for this employee."},
                    status=status.HTTP_404_NOT_FOUND,
                )

            serializer = EmployeeIdentityProofSerializer(identity_proof)
            return Response(serializer.data, status=status.HTTP_200_OK)

        document_type = request.data.get("document_type")
        document_number = request.data.get("document_number")
        file = request.FILES.get("file")

        if not document_type:
            return Response(
                {"detail": "document_type is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not document_number:
            return Response(
                {"detail": "document_number is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not file:
            return Response(
                {"detail": "file is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            identity_proof = create_identity_proof(
                employee=employee,
                document_type=document_type,
                document_number=document_number,
                file=file,
                uploaded_by=request.user,
            )
        except ValueError as exc:
            return Response(
                {"detail": str(exc)},
                status=status.HTTP_400_BAD_REQUEST,
            )
        send_employee_notification(
            employee=employee,
            title="Employee Identity Proof Uploaded",
            message=(
                f"Identity proof ({document_type}) was uploaded "
                f"for employee {employee} in {employee.branch.name}."
            ),
        )

        serializer = EmployeeIdentityProofSerializer(identity_proof)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


    @extend_schema(responses={200: OpenApiTypes.URI})
    @action(
        detail=True,
        methods=["get"],
        url_path="identity-proof/file",
    )
    def identity_proof_file(self, request, pk=None):
        employee = self.get_object()
        self.check_object_permissions(request, employee)

        try:
            url = get_identity_proof_file_url(employee=employee)
        except ValueError as exc:
            return Response(
                {"detail": str(exc)},
                status=status.HTTP_404_NOT_FOUND,
            )

        return Response({"url": url}, status=status.HTTP_200_OK)

    @extend_schema(
        request=EmployeeSalaryHistorySerializer,
        responses=EmployeeSalaryHistorySerializer,
    )
    @action(
        detail=True,
        methods=["get", "post"],
        url_path="salary-history",
    )
    def salary_history(self, request, pk=None):
        employee = self.get_object()

        if request.method == "GET":
            history = (
                employee.salary_history
                .select_related("created_by")
                .order_by("effective_from")
            )
            serializer = EmployeeSalaryHistorySerializer(history, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)

        permission = CanManageEmployeeSalary()
        if not permission.has_object_permission(request, self, employee):
            return Response(
                {
                    "detail": (
                        "You do not have permission to change "
                        "this employee's salary."
                    )
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        serializer = EmployeeSalaryHistorySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            salary_history = create_salary_revision(
                employee=employee,
                salary_type=serializer.validated_data["salary_type"],
                monthly_salary=serializer.validated_data.get("monthly_salary"),
                daily_wage=serializer.validated_data.get("daily_wage"),
                biweekly_salary=serializer.validated_data.get("biweekly_salary"),
                effective_from=serializer.validated_data["effective_from"],
                reason=serializer.validated_data.get("reason", ""),
                created_by=request.user,
            )
        except ValueError as exc:
            return Response(
                {"detail": str(exc)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        send_employee_notification(
            employee=employee,
            title="Employee Salary Revised",
            message=(
                f"The salary for employee {employee} has been revised. "
                f"Effective from {salary_history.effective_from}."
            ),
        )

        response_serializer = EmployeeSalaryHistorySerializer(salary_history)
        return Response(
            response_serializer.data,
            status=status.HTTP_201_CREATED,
        )
