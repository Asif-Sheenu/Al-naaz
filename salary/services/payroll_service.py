from django.db import transaction

from employees.models import Employee
from organization.services.access_service import (
    get_accessible_branches,
)

from .generate_salary import generate_salary


@transaction.atomic
def generate_all_salaries(
    *,
    user,
    month,
    year,
):
    """
    Generate salary for all active employees
    accessible to the given user.
    """

    employees = Employee.objects.filter(
        is_active=True,
    )

    # Branch access

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

        employees = employees.filter(
            branch_id__in=accessible_branch_ids
        )

    # Generate salaries

    salaries = []

    for employee in employees:

        salary = generate_salary(
            employee,
            month,
            year,
        )

        salaries.append(salary)

    return {
        "employees_processed": len(salaries),
        "salaries": salaries,
    }