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

    Employees whose salary already exists for the selected
    month/year are skipped.

    Employees with missing required salary data are also skipped,
    while the remaining employees continue processing.
    """

    employees = Employee.objects.filter(
        is_active=True,
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

        employees = employees.filter(
            branch_id__in=accessible_branch_ids
        )

    # --------------------------------
    # Generate salaries
    # --------------------------------

    salaries = []

    generated = []
    skipped = []
    failed = []

    for employee in employees:

        try:

            salary = generate_salary(
                employee,
                month,
                year,
            )

            salaries.append(salary)

            generated.append({
                "employee_id": employee.id,
                "employee_name": employee.name,
                "salary_id": salary.id,
            })

        except ValueError as e:

            skipped.append({
                "employee_id": employee.id,
                "employee_name": employee.name,
                "reason": str(e),
            })

        except Exception as e:

            failed.append({
                "employee_id": employee.id,
                "employee_name": employee.name,
                "reason": str(e),
            })

    return {
        "employees_processed": employees.count(),
        "generated_count": len(generated),
        "skipped_count": len(skipped),
        "failed_count": len(failed),
        "generated": generated,
        "skipped": skipped,
        "failed": failed,
    }