from decimal import Decimal
import calendar

from attendance.models import Attendance
from advance.models import Advance
from .models import Salary
from employees.models import Employee


def generate_salary(employee, month, year):
    """
    Generate or update salary for a single employee.
    """

    attendance = Attendance.objects.filter(
        employee=employee,
        date__month=month,
        date__year=year
    )

    present_days = attendance.filter(
        status=Attendance.Status.PRESENT
    ).count()

    half_days = attendance.filter(
        status=Attendance.Status.HALF_DAY
    ).count()

    absent_days = attendance.filter(
        status=Attendance.Status.ABSENT
    ).count()

    leave_days = attendance.filter(
        status=Attendance.Status.LEAVE
    ).count()

    working_days = calendar.monthrange(
        year,
        month
    )[1]

    # ----------------------------
    # Calculate Gross Salary
    # ----------------------------

    if employee.salary_type == Employee.SalaryType.MONTHLY:

        gross_salary = employee.monthly_salary or Decimal("0")

    elif employee.salary_type == Employee.SalaryType.DAILY:

        gross_salary = (
            Decimal(present_days) * (employee.daily_wage or Decimal("0"))
        ) + (
            Decimal(half_days)
            * ((employee.daily_wage or Decimal("0")) / Decimal("2"))
        )

    elif employee.salary_type == Employee.SalaryType.BIWEEKLY:

        gross_salary = employee.biweekly_salary or Decimal("0")

    else:

        gross_salary = Decimal("0")

    # ----------------------------
    # Approved Advance Deduction
    # ----------------------------

    advance_total = sum(
        Advance.objects.filter(
            employee=employee,
            status=Advance.Status.APPROVED,
            date__month=month,
            date__year=year
        ).values_list("amount", flat=True),
        Decimal("0")
    )

    # ----------------------------
    # Net Salary
    # ----------------------------

    net_salary = gross_salary - advance_total

    # Prevent negative salary

    if net_salary < Decimal("0"):
        net_salary = Decimal("0")

    # ----------------------------
    # Create / Update Salary
    # ----------------------------

    salary, created = Salary.objects.update_or_create(
        employee=employee,
        month=month,
        year=year,
        defaults={
            "salary_type": employee.salary_type,
            "working_days": working_days,
            "present_days": present_days,
            "half_days": half_days,
            "absent_days": absent_days,
            "leave_days": leave_days,
            "gross_salary": gross_salary,
            "advance_deduction": advance_total,
            "net_salary": net_salary,
        }
    )

    return salary