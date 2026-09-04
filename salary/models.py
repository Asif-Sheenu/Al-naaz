from django.db import models
from employees.models import Employee


class Salary(models.Model):

    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        PAID = "PAID", "Paid"

    employee = models.ForeignKey(
        Employee,
        on_delete=models.PROTECT,
        related_name="payrolls"
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

    attendance_deduction = models.DecimalField(
    max_digits=10,
    decimal_places=2,
    default=0,
    )

    advance_deduction = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0
    )

    other_deduction = models.DecimalField(
    max_digits=10,
    decimal_places=2,
    default=0,
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

        constraints = [
            models.UniqueConstraint(
                fields=["employee", "month", "year"],
                name="unique_salary_per_employee_month",
            )
        ]

        indexes = [
            models.Index(
                fields=["year", "month"],
                name="salary_year_month_idx",
            ),
            models.Index(
                fields=["employee", "year", "month"],
                name="salary_employee_period_idx",
            ),
            models.Index(
                fields=["status", "year", "month"],
                name="salary_status_period_idx",
            ),
        ]

    def __str__(self):
        return f"{self.employee.name} - {self.month}/{self.year}"

