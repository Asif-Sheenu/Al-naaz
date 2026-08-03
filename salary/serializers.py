# from rest_framework import serializers
# from .models import Salary


# class SalarySerializer(serializers.ModelSerializer):

#     employee_name = serializers.CharField(
#         source="employee.name",
#         read_only=True
#     )

#     class Meta:
#         model = Salary
#         fields = "__all__"