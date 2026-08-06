from django.shortcuts import render
from rest_framework import viewsets
from .services import generate_salary
from employees.models import Employee
from .models import Salary
from .serializers import SalarySerializer
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import status
from users.permissions import IsAdminOrStaff


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