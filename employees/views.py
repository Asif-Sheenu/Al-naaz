from django.shortcuts import render
from rest_framework import viewsets

from .models import Employee
from .serializers import EmployeeSerializer

from users.permissions import IsAdmin

# employee full crud 

class EmployeeViewSet(viewsets.ModelViewSet):

    queryset = Employee.objects.all().order_by("-id")

    serializer_class = EmployeeSerializer

    permission_classes = [IsAdmin]
