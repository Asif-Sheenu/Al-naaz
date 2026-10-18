from django.db import transaction
from django.utils import timezone

from ..models import Salary


@transaction.atomic
def mark_salary_as_paid(salary):
    """
    Mark a salary as paid safely.

    Locks the database row to prevent concurrent requests
    from paying the same salary simultaneously.
    """

    locked_salary = (
        Salary.objects
        .select_for_update()
        .get(pk=salary.pk)
    )

    if locked_salary.status == Salary.Status.PAID:
        raise ValueError("Salary is already paid.")

    locked_salary.status = Salary.Status.PAID
    locked_salary.payment_date = timezone.localdate()

    locked_salary.save(
        update_fields=[
            "status",
            "payment_date",
        ]
    )

    return locked_salary