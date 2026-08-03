from rest_framework import viewsets
from .models import Attendance
from .serializers import AttendanceSerializer
from users.permissions import IsAdminOrStaff


class AttendanceViewSet(viewsets.ModelViewSet):

    serializer_class = AttendanceSerializer
    permission_classes = [IsAdminOrStaff]

    def get_queryset(self):

        queryset = Attendance.objects.select_related("employee").order_by("-date")

        employee = self.request.query_params.get("employee")
        date = self.request.query_params.get("date")
        status = self.request.query_params.get("status")
        year = self.request.query_params.get("year")
        month = self.request.query_params.get("month")
        start_date = self.request.query_params.get("start_date")
        end_date = self.request.query_params.get("end_date")
        designation = self.request.query_params.get("designation")
        search = self.request.query_params.get("search")

        if employee:
            queryset = queryset.filter(employee_id=employee)

        if date:
            queryset = queryset.filter(date=date)

        if status:
            queryset = queryset.filter(status=status)

        if month:
            queryset = queryset.filter(date__month=month)

        if year:
            queryset = queryset.filter(date__year=year)

        if start_date and end_date:
            queryset = queryset.filter(
            date__range=[start_date, end_date]
        )
        if designation:
            queryset = queryset.filter(
                employee__designation__iexact=designation
            )

        if search:
            queryset = queryset.filter(
                employee__name__icontains=search
            )
    

        return queryset