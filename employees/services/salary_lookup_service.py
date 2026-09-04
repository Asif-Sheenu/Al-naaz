from django.db.models import Q

from employees.models import EmployeeSalaryHistory


def get_salary_for_date(employee, target_date):
    """
    Return the salary history record that was effective
    on the given date.
    """

    return (
        EmployeeSalaryHistory.objects
        .filter(
            employee=employee,
            effective_from__lte=target_date,
        )
        .filter(
            Q(effective_to__isnull=True)
            | Q(effective_to__gte=target_date)
        )
        .order_by("-effective_from")
        .first()
    )