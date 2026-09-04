from django.db.models import Sum

from advance.models import Advance
from employees.models import Employee
from organization.services.access_service import get_accessible_branches
from ..models import Salary


def get_payroll_dashboard(*, user, month, year):

    # -------------------------------------------------
    # Employees
    # -------------------------------------------------

    employees = Employee.objects.all()

    # -------------------------------------------------
    # Salaries
    # -------------------------------------------------

    salaries = Salary.objects.all()

    # -------------------------------------------------
    # Advances
    # -------------------------------------------------

    advances = Advance.objects.all()

    # -------------------------------------------------
    # Branch access
    # -------------------------------------------------

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

        salaries = salaries.filter(
            employee__branch_id__in=accessible_branch_ids
        )

        advances = advances.filter(
            employee__branch_id__in=accessible_branch_ids
        )

    # -------------------------------------------------
    # Employee statistics
    # -------------------------------------------------

    total_employees = employees.count()

    active_employees = employees.filter(
        is_active=True
    ).count()

    # -------------------------------------------------
    # Salary statistics
    # -------------------------------------------------

    monthly_salaries = salaries.filter(
        month=month,
        year=year,
    )

    paid_salaries = monthly_salaries.filter(
        status=Salary.Status.PAID
    ).count()

    pending_salaries = monthly_salaries.filter(
        status=Salary.Status.PENDING
    ).count()

    total_payroll = (
        monthly_salaries.aggregate(
            total=Sum("gross_salary")
        )["total"]
        or 0
    )

    total_net_salary = (
        monthly_salaries.aggregate(
            total=Sum("net_salary")
        )["total"]
        or 0
    )

    # -------------------------------------------------
    # Advance statistics
    # -------------------------------------------------

    monthly_advances = advances.filter(
        status=Advance.Status.APPROVED,
        date__month=month,
        date__year=year,
    )

    total_advance = (
        monthly_advances.aggregate(
            total=Sum("amount")
        )["total"]
        or 0
    )

    employees_with_approved_advance = (
        monthly_advances
        .values("employee")
        .distinct()
        .count()
    )

    pending_advance_requests = (
        advances
        .filter(status=Advance.Status.PENDING)
        .count()
    )

    # -------------------------------------------------
    # Final dashboard data
    # -------------------------------------------------

    return {
        "total_employees": total_employees,
        "active_employees": active_employees,
        "paid_salaries": paid_salaries,
        "pending_salaries": pending_salaries,
        "employees_with_approved_advance": (
            employees_with_approved_advance
        ),
        "pending_advance_requests": (
            pending_advance_requests
        ),
        "approved_advances": monthly_advances.count(),
        "total_payroll": total_payroll,
        "total_advance": total_advance,
        "total_net_salary": total_net_salary,
        "month": month,
        "year": year,
    }