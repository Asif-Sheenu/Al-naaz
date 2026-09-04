from rest_framework import serializers

from employees.models import Employee


def validate_salary_data(
    salary_type,
    monthly_salary=None,
    daily_wage=None,
    biweekly_salary=None,
):
    if salary_type == Employee.SalaryType.MONTHLY:

        if monthly_salary is None:
            raise serializers.ValidationError({
                "monthly_salary": (
                    "Monthly salary is required "
                    "for MONTHLY salary type."
                )
            })

        if monthly_salary <= 0:
            raise serializers.ValidationError({
                "monthly_salary": (
                    "Monthly salary must be greater than zero."
                )
            })

        if daily_wage is not None:
            raise serializers.ValidationError({
                "daily_wage": (
                    "Daily wage must be empty "
                    "for MONTHLY salary type."
                )
            })

        if biweekly_salary is not None:
            raise serializers.ValidationError({
                "biweekly_salary": (
                    "Biweekly salary must be empty "
                    "for MONTHLY salary type."
                )
            })

    elif salary_type == Employee.SalaryType.DAILY:

        if daily_wage is None:
            raise serializers.ValidationError({
                "daily_wage": (
                    "Daily wage is required "
                    "for DAILY salary type."
                )
            })

        if daily_wage <= 0:
            raise serializers.ValidationError({
                "daily_wage": (
                    "Daily wage must be greater than zero."
                )
            })

        if monthly_salary is not None:
            raise serializers.ValidationError({
                "monthly_salary": (
                    "Monthly salary must be empty "
                    "for DAILY salary type."
                )
            })

        if biweekly_salary is not None:
            raise serializers.ValidationError({
                "biweekly_salary": (
                    "Biweekly salary must be empty "
                    "for DAILY salary type."
                )
            })

    elif salary_type == Employee.SalaryType.BIWEEKLY:

        if biweekly_salary is None:
            raise serializers.ValidationError({
                "biweekly_salary": (
                    "Biweekly salary is required "
                    "for BIWEEKLY salary type."
                )
            })

        if biweekly_salary <= 0:
            raise serializers.ValidationError({
                "biweekly_salary": (
                    "Biweekly salary must be greater than zero."
                )
            })

        if monthly_salary is not None:
            raise serializers.ValidationError({
                "monthly_salary": (
                    "Monthly salary must be empty "
                    "for BIWEEKLY salary type."
                )
            })

        if daily_wage is not None:
            raise serializers.ValidationError({
                "daily_wage": (
                    "Daily wage must be empty "
                    "for BIWEEKLY salary type."
                )
            })

    return True