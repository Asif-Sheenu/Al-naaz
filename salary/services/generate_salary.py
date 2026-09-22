from calendar import monthrange
from datetime import date
from decimal import Decimal, ROUND_HALF_UP

from django.db import models, transaction

from advance.models import Advance
from employees.models import Employee
from employees.services.salary_lookup_service import get_salary_for_date

from ..models import Salary
from .helpers import calculate_attendance


def money(value):
    return Decimal(value).quantize(
        Decimal("0.01"),
        rounding=ROUND_HALF_UP,
    )


@transaction.atomic
def generate_salary(employee, month, year):
    """
    Generate salary for a single employee
    for the given month and year.

    Rules:
    - Salary can only be generated once for an employee/month/year.
    - Existing PENDING salary cannot be regenerated.
    - Existing PAID salary cannot be regenerated.
    - Required salary configuration must exist.
    - Monthly salary requires working_days > 0.
    - Approved advances for the payroll month are deducted.
    """

    # --------------------------------------------------
    # 1. Basic validation
    # --------------------------------------------------

    if not employee.is_active:
        raise ValueError(
            f"Employee '{employee.name}' is inactive."
        )

    if not month or month < 1 or month > 12:
        raise ValueError(
            "Invalid payroll month."
        )

    if not year or year < 2000:
        raise ValueError(
            "Invalid payroll year."
        )

    # --------------------------------------------------
    # 2. Prevent regeneration
    # --------------------------------------------------

    existing_salary = Salary.objects.filter(
        employee=employee,
        month=month,
        year=year,
    ).first()

    if existing_salary:

        if existing_salary.status == Salary.Status.PAID:
            raise ValueError(
                f"Salary for {employee.name} "
                f"for {month}/{year} has already been paid "
                "and cannot be regenerated."
            )

        raise ValueError(
            f"Salary for {employee.name} "
            f"for {month}/{year} has already been generated."
        )

    # --------------------------------------------------
    # 3. Attendance calculation
    # --------------------------------------------------

    attendance_data = calculate_attendance(
        employee,
        month,
        year,
    )

    working_days = attendance_data["working_days"]
    present_days = attendance_data["present_days"]
    absent_days = attendance_data["absent_days"]
    half_days = attendance_data["half_days"]
    leave_days = attendance_data["leave_days"]
    unpaid_days = attendance_data["unpaid_days"]

    # --------------------------------------------------
    # 4. Validate attendance data
    # --------------------------------------------------

    if working_days < 0:
        raise ValueError(
            "Invalid working days calculated."
        )

    if present_days < 0:
        raise ValueError(
            "Invalid present days calculated."
        )

    if absent_days < 0:
        raise ValueError(
            "Invalid absent days calculated."
        )

    if half_days < 0:
        raise ValueError(
            "Invalid half days calculated."
        )

    if leave_days < 0:
        raise ValueError(
            "Invalid leave days calculated."
        )

    if unpaid_days < 0:
        raise ValueError(
            "Invalid unpaid days calculated."
        )

    # --------------------------------------------------
    # 5. Find salary history effective for payroll period
    # --------------------------------------------------

    payroll_date = date(
        year,
        month,
        monthrange(year, month)[1],
    )

    salary_history = get_salary_for_date(
        employee,
        payroll_date,
    )

    if not salary_history:
        raise ValueError(
            f"No salary history found for {employee.name} "
            f"for {month}/{year}."
        )

    # --------------------------------------------------
    # 6. Calculate gross salary
    # --------------------------------------------------

    salary_type = salary_history.salary_type

    # -----------------------------------------------
    # MONTHLY
    # -----------------------------------------------

    if salary_type == Employee.SalaryType.MONTHLY:

        if not salary_history.monthly_salary:
            raise ValueError(
                f"Monthly salary is not configured for "
                f"{employee.name}."
            )

        if salary_history.monthly_salary <= Decimal("0.00"):
            raise ValueError(
                f"Monthly salary must be greater than zero "
                f"for {employee.name}."
            )

        if working_days <= 0:
            raise ValueError(
                f"Cannot generate monthly salary for "
                f"{employee.name}: working days are zero."
            )

        monthly_salary = money(
            salary_history.monthly_salary
        )

        gross_salary = monthly_salary

        # Daily rate based on working days
        daily_rate = (
            monthly_salary
            / Decimal(working_days)
        )

        attendance_deduction = money(
            daily_rate
            * Decimal(unpaid_days)
        )

    # -----------------------------------------------
    # DAILY
    # -----------------------------------------------

    elif salary_type == Employee.SalaryType.DAILY:

        if not salary_history.daily_wage:
            raise ValueError(
                f"Daily wage is not configured for "
                f"{employee.name}."
            )

        if salary_history.daily_wage <= Decimal("0.00"):
            raise ValueError(
                f"Daily wage must be greater than zero "
                f"for {employee.name}."
            )

        daily_wage = money(
            salary_history.daily_wage
        )

        # Full day = 100%
        # Half day = 50%

        gross_salary = money(
            (
                Decimal(present_days)
                * daily_wage
            )
            + (
                Decimal(half_days)
                * (
                    daily_wage
                    / Decimal("2")
                )
            )
        )

        attendance_deduction = Decimal(
            "0.00"
        )

    # -----------------------------------------------
    # BIWEEKLY
    # -----------------------------------------------

    elif salary_type == Employee.SalaryType.BIWEEKLY:

        if not salary_history.biweekly_salary:
            raise ValueError(
                f"Biweekly salary is not configured for "
                f"{employee.name}."
            )

        if salary_history.biweekly_salary <= Decimal("0.00"):
            raise ValueError(
                f"Biweekly salary must be greater than zero "
                f"for {employee.name}."
            )

        gross_salary = money(
            salary_history.biweekly_salary
        )

        attendance_deduction = Decimal(
            "0.00"
        )

    # -----------------------------------------------
    # INVALID SALARY TYPE
    # -----------------------------------------------

    else:

        raise ValueError(
            f"Invalid salary type configured for "
            f"{employee.name}."
        )

    # --------------------------------------------------
    # 7. Approved advance deduction
    # --------------------------------------------------

    advance_total = (
        Advance.objects
        .filter(
            employee=employee,
            status=Advance.Status.APPROVED,
            date__month=month,
            date__year=year,
        )
        .aggregate(
            total=models.Sum("amount")
        )["total"]
        or Decimal("0.00")
    )

    advance_total = money(
        advance_total
    )

    # --------------------------------------------------
    # 8. Other deductions
    # --------------------------------------------------

    other_deduction = Decimal(
        "0.00"
    )

    # --------------------------------------------------
    # 9. Calculate net salary
    # --------------------------------------------------

    net_salary = (
        gross_salary
        - attendance_deduction
        - advance_total
        - other_deduction
    )

    # Salary cannot be negative
    if net_salary < Decimal("0.00"):
        net_salary = Decimal("0.00")

    net_salary = money(
        net_salary
    )

    # --------------------------------------------------
    # 10. Create salary record
    # --------------------------------------------------

    salary = Salary.objects.create(
        employee=employee,
        month=month,
        year=year,
        salary_type=salary_type,

        working_days=working_days,
        present_days=present_days,
        absent_days=absent_days,
        half_days=half_days,
        leave_days=leave_days,

        gross_salary=gross_salary,
        attendance_deduction=attendance_deduction,
        advance_deduction=advance_total,
        other_deduction=other_deduction,
        net_salary=net_salary,
    )

    return salary