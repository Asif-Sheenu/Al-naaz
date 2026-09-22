from rest_framework import viewsets
from .services import (
    generate_salary,
    generate_all_salaries,
    mark_salary_as_paid,
    get_payroll_dashboard)
from employees.models import Employee
from .models import Salary
from .serializers import SalarySerializer,SalaryGenerateSerializer ,PayrollDashboardSerializer ,SalaryGenerateAllResponseSerializer,SalaryGenerateAllSerializer
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import status
from .permissions import CanManageSalary
from django.utils import timezone
from drf_spectacular.utils import extend_schema
from advance.models import Advance
from django.db.models import Sum
from django.http import FileResponse
from .pdf import generate_payslip_pdf
from organization.services.access_service import get_accessible_branches

class SalaryViewSet(viewsets.ReadOnlyModelViewSet):

    serializer_class = SalarySerializer

    permission_classes = [CanManageSalary]

    def get_queryset(self):

        user = self.request.user

        queryset = Salary.objects.select_related(
            "employee",
            "employee__branch",
        ).order_by(
            "-year",
            "-month",
        )

        # --------------------------------
        # Branch access
        # --------------------------------

        if not (
            user.is_superuser
            or user.role == "ADMIN"
        ):

            accessible_branch_ids = (
                get_accessible_branches(user)
                .values_list(
                    "id",
                    flat=True,
                )
            )

            queryset = queryset.filter(
                employee__branch_id__in=accessible_branch_ids
            )

        # --------------------------------
        # Filters
        # --------------------------------

        employee = self.request.query_params.get(
            "employee"
        )

        month = self.request.query_params.get(
            "month"
        )

        year = self.request.query_params.get(
            "year"
        )

        salary_status = self.request.query_params.get(
            "status"
        )

        search = self.request.query_params.get(
            "search"
        )

        if employee:
            queryset = queryset.filter(
                employee_id=employee
            )

        if month:
            queryset = queryset.filter(
                month=month
            )

        if year:
            queryset = queryset.filter(
                year=year
            )

        if salary_status:
            queryset = queryset.filter(
                status=salary_status
            )

        if search:
            queryset = queryset.filter(
                employee__name__icontains=search
            )

        return queryset


    @extend_schema(
    request=SalaryGenerateSerializer,
    responses=SalarySerializer,
    )
    @action(
        detail=False,
        methods=["post"],
        permission_classes=[CanManageSalary],
    )
    def generate(self, request):

        serializer = SalaryGenerateSerializer(
            data=request.data
        )

        serializer.is_valid(
            raise_exception=True
        )

        employee_id = serializer.validated_data["employee"]
        month = serializer.validated_data["month"]
        year = serializer.validated_data["year"]

        try:
            employee = Employee.objects.select_related(
                "branch"
            ).get(
                id=employee_id,
                is_active=True,
            )

        except Employee.DoesNotExist:
            return Response(
                {
                    "error": "Employee not found."
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        # --------------------------------
        # Branch access
        # --------------------------------

        user = request.user

        if not (
            user.is_superuser
            or user.role == "ADMIN"
        ):

            accessible_branch_ids = (
                get_accessible_branches(user)
                .values_list(
                    "id",
                    flat=True,
                )
            )

            if employee.branch_id not in accessible_branch_ids:
                return Response(
                    {
                        "error": (
                            "You do not have access to "
                            "this employee's branch."
                        )
                    },
                    status=status.HTTP_403_FORBIDDEN,
                )

        # --------------------------------
        # Generate salary
        # --------------------------------

        try:
            salary = generate_salary(
                employee,
                month,
                year,
            )

        except ValueError as exc:
            return Response(
                {
                    "error": str(exc)
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = self.get_serializer(salary)

        return Response(
            serializer.data,
            status=status.HTTP_200_OK,
        )
# mark as paid -----------------------------------------------
# 
    @extend_schema(
    request=None,
    responses=SalarySerializer,
    )
    @action(
        detail=True,
        methods=["post"],
    )
    def pay(self, request, pk=None):

        salary = self.get_object()

        try:
            salary = mark_salary_as_paid(salary)

        except ValueError as exc:
            return Response(
                {
                    "error": str(exc)
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = self.get_serializer(salary)

        return Response(
            {
                "message": "Salary paid successfully.",
                "salary": serializer.data,
            },
            status=status.HTTP_200_OK,
        )

    # all employee Salary-----------------------------
    @extend_schema(
    request=SalaryGenerateAllSerializer,
    responses={200: SalaryGenerateAllResponseSerializer},
    )
    @action(
    detail=False,
    methods=["post"],
    url_path="generate_all",
)
    def generate_all(self, request):

        serializer = SalaryGenerateAllSerializer(
            data=request.data
        )

        serializer.is_valid(
            raise_exception=True
        )

        month = serializer.validated_data["month"]
        year = serializer.validated_data["year"]

        result = generate_all_salaries(
            user=request.user,
            month=month,
            year=year,
        )

        return Response(
            result,
            status=status.HTTP_200_OK,
        )


# admin salary dashboardd =-----------------------------------------
# 
    @extend_schema(
    responses=PayrollDashboardSerializer,
    )
    @action(
        detail=False,
        methods=["get"],
    )
    def dashboard(self, request):

        today = timezone.now()

        result = get_payroll_dashboard(
            user=request.user,
            month=today.month,
            year=today.year,
        )

        serializer = PayrollDashboardSerializer(result)

        return Response(
            serializer.data,
            status=status.HTTP_200_OK,
        )


# salary pdf ==----------------------------

    @action(detail=True, methods=["get"])
    def payslip(self, request, pk=None):

        salary = self.get_object()

        pdf_buffer = generate_payslip_pdf(salary)

        filename = (
            f"payslip_{salary.employee.name}_"
            f"{salary.month}_{salary.year}.pdf"
        )

        return FileResponse(
            pdf_buffer,
            as_attachment=True,
            filename=filename,
            content_type="application/pdf",
        )