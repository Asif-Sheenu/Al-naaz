# from django.shortcuts import render
# from rest_framework import viewsets

# from .models import Salary
# from .serializers import SalarySerializer

# from users.permissions import IsAdminOrStaff


# class SalaryViewSet(viewsets.ModelViewSet):

#     serializer_class = SalarySerializer

#     permission_classes = [IsAdminOrStaff]

#     def get_queryset(self):

#         queryset = Salary.objects.select_related(
#             "employee"
#         ).order_by("-year", "-month")

#         employee = self.request.query_params.get("employee")
#         month = self.request.query_params.get("month")
#         year = self.request.query_params.get("year")
#         status = self.request.query_params.get("status")
#         search = self.request.query_params.get("search")

#         if employee:
#             queryset = queryset.filter(employee_id=employee)

#         if month:
#             queryset = queryset.filter(month=month)

#         if year:
#             queryset = queryset.filter(year=year)

#         if status:
#             queryset = queryset.filter(status=status)

#         if search:
#             queryset = queryset.filter(
#                 employee__name__icontains=search
#             )
 
#         return queryset