from decimal import Decimal
import calendar

from attendance.models import Attendance


def calculate_attendance(
    employee,
    month,
    year,
):
    """
    Calculate attendance information used by payroll.

    Business rules that are not yet finalized
    (leave and half-day policies) are intentionally
    kept simple for now.
    """

    attendance = Attendance.objects.filter(
        employee=employee,
        date__month=month,
        date__year=year,
    )

    present_days = attendance.filter(
        status=Attendance.Status.PRESENT
    ).count()

    absent_days = attendance.filter(
        status=Attendance.Status.ABSENT
    ).count()

    half_days = attendance.filter(
        status=Attendance.Status.HALF_DAY
    ).count()

    leave_days = attendance.filter(
        status=Attendance.Status.LEAVE
    ).count()

    unpaid_days = attendance.filter(
        is_paid=False
    ).count()

    working_days = calendar.monthrange(
        year,
        month,
    )[1]

    return {
        "working_days": working_days,
        "present_days": present_days,
        "absent_days": absent_days,
        "half_days": half_days,
        "leave_days": leave_days,
        "unpaid_days": unpaid_days,
    }