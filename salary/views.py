from django.shortcuts import render
from rest_framework import viewsets
from .services import generate_salary
from employees.models import Employee
from .models import Salary
from .serializers import SalarySerializer,SalaryGenerateSerializer ,PayrollDashboardSerializer 
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import status
from users.permissions import IsAdminOrStaff
from django.utils import timezone
from drf_spectacular.utils import extend_schema
from advance.models import Advance
from django.db.models import Sum, Count, Q
from django.http import FileResponse
from .pdf import generate_payslip_pdf


class SalaryViewSet(viewsets.ModelViewSet):

    serializer_class = SalarySerializer

    permission_classes = [IsAdminOrStaff]

    def get_queryset(self):

        queryset = Salary.objects.select_related(
            "employee"
        ).order_by("-year", "-month")

        employee = self.request.query_params.get("employee")
        month = self.request.query_params.get("month")
        year = self.request.query_params.get("year")
        status = self.request.query_params.get("status")
        search = self.request.query_params.get("search")

        if employee:
            queryset = queryset.filter(employee_id=employee)

        if month:
            queryset = queryset.filter(month=month)

        if year:
            queryset = queryset.filter(year=year)

        if status:
            queryset = queryset.filter(status=status)

        if search:
            queryset = queryset.filter(
                employee__name__icontains=search
            )
 
        return queryset

    @action(
    detail=False,
    methods=["post"],
    permission_classes=[IsAdminOrStaff]
    )
    def generate(self, request):

        employee_id = request.data.get("employee")
        month = request.data.get("month")
        year = request.data.get("year")

        if not employee_id or not month or not year:
            return Response(
                {
                    "error": "employee, month and year are required."
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            employee = Employee.objects.get(id=employee_id)

        except Employee.DoesNotExist:
            return Response(
                {
                    "error": "Employee not found."
                },
                status=status.HTTP_404_NOT_FOUND
            )

        salary = generate_salary(
            employee,
            int(month),
            int(year)
        )

        serializer = self.get_serializer(salary)

        return Response(
            serializer.data,
            status=status.HTTP_200_OK
        )


# mark as paid -----------------------------------------------
# 

    @action(detail=True, methods=["post"])
    def pay(self, request, pk=None):

        salary = self.get_object()

        if salary.status == Salary.Status.PAID:
            return Response(
                {
                    "message": "Salary is already paid."
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        salary.status = Salary.Status.PAID
        salary.payment_date = timezone.now().date()
        salary.save()

        return Response(
            {
                "message": "Salary paid successfully."
            }
        )

    # all employee Salary-----------------------------
    @extend_schema(
    request=SalaryGenerateSerializer,
    responses={200: None},
    )
    @action(detail=False, methods=["post"])
    def generate_all(self, request):

        serializer = SalaryGenerateSerializer(
            data=request.data
        )

        serializer.is_valid(raise_exception=True)

        month = serializer.validated_data["month"]
        year = serializer.validated_data["year"]

        employees = Employee.objects.filter(
            is_active=True
        )

        count = 0

        for employee in employees:
            generate_salary(
                employee,
                month,
                year
            )
            count += 1

        return Response(
            {
                "message": "Salary generated successfully.",
                "employees_processed": count
            }
        )



# admin salary dashboardd =-----------------------------------------
# 
    @action(detail=False, methods=["get"])
    def dashboard(self, request):

        today = timezone.now()

        month = today.month
        year = today.year    
        total_employees = Employee.objects.count()
        active_employees = Employee.objects.filter(is_active=True).count()

        paid_salaries = Salary.objects.filter(
                        month=month,year=year,status=Salary.Status.PAID).count()
        pending_salaries = Salary.objects.filter(
            month=month,
            year=year,
            status=Salary.Status.PENDING).count()
        total_payroll = (
        Salary.objects.filter(month=month,
                        year=year).aggregate(total=Sum("gross_salary"))["total"] or 0)
        total_advance = (Advance.objects.filter(
                            status=Advance.Status.APPROVED,
                            date__month=month,
                            date__year=year).aggregate(total=Sum("amount")
                            )["total"] or 0)
        total_net_salary = (Salary.objects.filter(
                            month=month,year=year).aggregate(
                            total=Sum("net_salary"))["total"] or 0)
        employees_with_approved_advance = (Advance.objects.filter(
                                            status=Advance.Status.APPROVED,
                                            date__month=month,
                                            date__year=year).values("employee")
                                            .distinct()
                                            .count())
        pending_advance_requests = (Advance.objects.filter(status=Advance.Status.PENDING
                                    ).count())                            
        
        return Response({
    "total_employees": total_employees,
    "active_employees": active_employees,
    "paid_salaries": paid_salaries,
    "pending_salaries": pending_salaries,
    "employees_with_approved_advance": employees_with_approved_advance,
    "pending_advance_requests": pending_advance_requests,
    "total_payroll": total_payroll,
    "total_advance": total_advance,
    "total_net_salary": total_net_salary,
    "month": month,
    "year": year,
    })



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