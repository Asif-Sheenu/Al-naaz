from datetime import timedelta

from django.db import transaction
from django.utils import timezone

from ..models import EmployeeSalaryHistory


@transaction.atomic
def create_salary_revision(
    *,
    employee,
    salary_type,
    monthly_salary=None,
    daily_wage=None,
    biweekly_salary=None,
    effective_from,
    reason="",
    created_by,
):
    
    previous_salary = (
        EmployeeSalaryHistory.objects
        .filter(
            employee=employee,
            effective_from__lt=effective_from,
        )
        .order_by("-effective_from")
        .first()
    )

    # Find any revision that already starts on/after the
    # new effective date.
    next_salary = (
        EmployeeSalaryHistory.objects
        .filter(
            employee=employee,
            effective_from__gte=effective_from,
        )
        .order_by("effective_from")
        .first()
    )

 
    if next_salary and next_salary.effective_from == effective_from:
        raise ValueError(
            "A salary revision already exists for this effective date."
        )

    if previous_salary:
        previous_salary.effective_to = effective_from - timedelta(days=1)

        previous_salary.save(
            update_fields=["effective_to"]
        )

    effective_to = None

    if next_salary:
        effective_to = next_salary.effective_from - timedelta(days=1)

    salary_history = EmployeeSalaryHistory.objects.create(
        employee=employee,
        salary_type=salary_type,
        monthly_salary=monthly_salary,
        daily_wage=daily_wage,
        biweekly_salary=biweekly_salary,
        effective_from=effective_from,
        effective_to=effective_to,
        reason=reason,
        created_by=created_by,
    )

   
    today = timezone.localdate()

    if effective_from <= today:
        employee.salary_type = salary_type
        employee.monthly_salary = monthly_salary
        employee.daily_wage = daily_wage
        employee.biweekly_salary = biweekly_salary

        employee.save(
            update_fields=[
                "salary_type",
                "monthly_salary",
                "daily_wage",
                "biweekly_salary",
                "updated_at",
            ]
        )

    return salary_history