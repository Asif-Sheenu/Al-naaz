from django.db import models
from employees.models import Employee


class Salary(models.Model):

    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        PAID = "PAID", "Paid"

    employee = models.ForeignKey(
        Employee,
        on_delete=models.CASCADE,
        related_name="payrolls"
    )

    generated_at = models.DateTimeField(
    auto_now_add=True
    )

    month = models.PositiveSmallIntegerField()

    year = models.PositiveSmallIntegerField()

    # Snapshot of salary type
    salary_type = models.CharField(
        max_length=20
    )

    # Attendance Summary
    working_days = models.PositiveIntegerField(default=0)

    present_days = models.PositiveIntegerField(default=0)

    absent_days = models.PositiveIntegerField(default=0)

    # Salary
    gross_salary = models.DecimalField(
        max_digits=10,
        decimal_places=2
    )

    advance_deduction = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0
    )

    net_salary = models.DecimalField(
        max_digits=10,
        decimal_places=2
    )

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING
    )

    payment_date = models.DateField(
        null=True,
        blank=True
    )

    leave_days = models.PositiveIntegerField(default=0)

    half_days = models.PositiveIntegerField(default=0)

    remarks = models.TextField(
        blank=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    class Meta:
        ordering = ["-year", "-month"]
        unique_together = ("employee", "month", "year")

    def __str__(self):
        return f"{self.employee.name} - {self.month}/{self.year}"