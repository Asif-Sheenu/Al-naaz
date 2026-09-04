from django.db import transaction
from django.utils import timezone

from ..models import Salary


@transaction.atomic
def mark_salary_as_paid(salary):
    """
    Mark a pending salary as paid.
    """

    if salary.status == Salary.Status.PAID:
        raise ValueError(
            "Salary is already paid."
        )

    salary.status = Salary.Status.PAID
    salary.payment_date = timezone.now().date()

    salary.save(
        update_fields=[
            "status",
            "payment_date",
        ]
    )

    return salary