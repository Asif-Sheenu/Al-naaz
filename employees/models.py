from django.db import models

class Employee(models.Model):

    class SalaryType(models.TextChoices):
        MONTHLY = "MONTHLY", "Monthly"
        DAILY = "DAILY", "Daily"
        BIWEEKLY = "BIWEEKLY", "15 Days"

    name = models.CharField(max_length=100)

    phone = models.CharField(max_length=15)

    address = models.TextField(blank=True)

    designation = models.CharField(max_length=100)

    salary_type = models.CharField(
    max_length=20,
    choices=SalaryType.choices,
    default=SalaryType.MONTHLY
    )

    biweekly_salary = models.DecimalField(
    max_digits=10,
    decimal_places=2,
    null=True,
    blank=True
    )

    monthly_salary = models.DecimalField(
    max_digits=10,
    decimal_places=2,
    null=True,
    blank=True
    )

    daily_wage = models.DecimalField(
    max_digits=10,
    decimal_places=2,
    null=True,
    blank=True
    )

    joining_date = models.DateField()

    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)

    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name