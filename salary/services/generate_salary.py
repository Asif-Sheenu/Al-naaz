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
    Generate or update salary for a single employee
    for the given month and year.

    Salary calculation uses the salary history that was
    effective for the payroll period.
    """

    # Attendance calculation

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

    # Find effective salary

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
            "No salary history found for this employee "
            "for the selected payroll period."
        )

    # Calculate gross salary

    if salary_history.salary_type == Employee.SalaryType.MONTHLY:

        monthly_salary = (
            salary_history.monthly_salary
            or Decimal("0")
        )

        gross_salary = money(monthly_salary)

        # Attendance deduction
        daily_rate = (
            monthly_salary
            / Decimal(working_days)
        )

        attendance_deduction = money(
            daily_rate
            * Decimal(unpaid_days)
        )

    elif salary_history.salary_type == Employee.SalaryType.DAILY:

        daily_wage = (
            salary_history.daily_wage
            or Decimal("0")
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
                * (daily_wage / Decimal("2"))
            )
        )

        attendance_deduction = Decimal("0.00")

    elif salary_history.salary_type == Employee.SalaryType.BIWEEKLY:

        gross_salary = money(
            salary_history.biweekly_salary
            or Decimal("0")
        )

        attendance_deduction = Decimal("0.00")

    else:

        gross_salary = Decimal("0.00")
        attendance_deduction = Decimal("0.00")

    # Approved advance deduction

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

    advance_total = money(advance_total)

    # Other deductions

    other_deduction = Decimal("0.00")

    # Calculate net salary

    net_salary = (
        gross_salary
        - attendance_deduction
        - advance_total
        - other_deduction
    )

    if net_salary < Decimal("0.00"):
        net_salary = Decimal("0.00")

    net_salary = money(net_salary)

    # Create / update payroll

    # Create / update payroll

    existing_salary = Salary.objects.filter(
        employee=employee,
        month=month,
        year=year,
    ).first()

    if existing_salary:

        # --------------------------------
        # Protect paid payroll
        # --------------------------------

        if existing_salary.status == Salary.Status.PAID:
            raise ValueError(
                "Salary has already been paid and cannot be regenerated."
            )

        # --------------------------------
        # Update pending payroll
        # --------------------------------

        salary = existing_salary

        salary.salary_type = salary_history.salary_type
        salary.working_days = working_days
        salary.present_days = present_days
        salary.half_days = half_days
        salary.absent_days = absent_days
        salary.leave_days = leave_days
        salary.gross_salary = gross_salary
        salary.attendance_deduction = attendance_deduction
        salary.advance_deduction = advance_total
        salary.other_deduction = other_deduction
        salary.net_salary = net_salary

        salary.save()

    else:

        # --------------------------------
        # Create new payroll
        # --------------------------------

        salary = Salary.objects.create(
            employee=employee,
            month=month,
            year=year,
            salary_type=salary_history.salary_type,
            working_days=working_days,
            present_days=present_days,
            half_days=half_days,
            absent_days=absent_days,
            leave_days=leave_days,
            gross_salary=gross_salary,
            attendance_deduction=attendance_deduction,
            advance_deduction=advance_total,
            other_deduction=other_deduction,
            net_salary=net_salary,
        )

    return salary                                       