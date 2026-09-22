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

    Existing salaries for the selected month/year
    are skipped.

    Employees without required salary data are skipped.
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
    # Results
    # --------------------------------

    generated = []
    skipped = []

    for employee in employees:

        try:

            salary = generate_salary(
                employee,
                month,
                year,
            )

            generated.append({
                "salary_id": salary.id,
                "employee_id": employee.id,
                "employee_name": employee.name,

                "month": salary.month,
                "year": salary.year,

                "salary_type": salary.salary_type,

                "working_days": salary.working_days,
                "present_days": salary.present_days,
                "absent_days": salary.absent_days,

                "leave_days": salary.leave_days,
                "half_days": salary.half_days,

                "gross_salary": salary.gross_salary,
                "attendance_deduction": salary.attendance_deduction,
                "advance_deduction": salary.advance_deduction,
                "other_deduction": salary.other_deduction,

                "net_salary": salary.net_salary,

                "status": salary.status,

                "payment_date": salary.payment_date,

                "remarks": salary.remarks,

                "created_at": salary.created_at,
            })

        except ValueError as e:

            skipped.append({
                "employee_id": employee.id,
                "employee_name": employee.name,
                "reason": str(e),
            })

    return {
        "employees_processed": employees.count(),

        "generated_count": len(generated),

        "skipped_count": len(skipped),

        "failed_count": 0,

        "generated": generated,

        "skipped": skipped,

        "failed": [],
    }