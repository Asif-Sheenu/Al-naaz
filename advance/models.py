from django.db import models
from employees.models import Employee
from django.conf import settings



class Advance(models.Model):


    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        APPROVED = "APPROVED", "Approved"
        REJECTED = "REJECTED", "Rejected"

    employee = models.ForeignKey(
        Employee,
        on_delete=models.CASCADE,
        related_name="advances"
    )

    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2
    )

    date = models.DateField()

    reason = models.CharField(
        max_length=255,
        blank=True
    )

    remarks = models.TextField(
        blank=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    status = models.CharField(
    max_length=20,
    choices=Status.choices,
    default=Status.PENDING
    )
    
    requested_by = models.ForeignKey(
    settings.AUTH_USER_MODEL,
    on_delete=models.SET_NULL,
    null=True,
    blank=True,
    related_name="requested_advances"
)
    approved_by = models.ForeignKey(
    settings.AUTH_USER_MODEL,
    on_delete=models.SET_NULL,
    null=True,
    blank=True,
    related_name="approved_advances"
)

    approved_at = models.DateTimeField(
    null=True,
    blank=True
    )

    def __str__(self):
        return f"{self.employee.name} - ₹{self.amount}"