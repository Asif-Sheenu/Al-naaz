# from django.db import models
# from django.db import models
# from employees.models import Employee


# class Salary(models.Model):

#     class Status(models.TextChoices):
#         PENDING = "PENDING", "Pending"
#         PAID = "PAID", "Paid"

#     employee = models.ForeignKey(
#         Employee,
#         on_delete=models.CASCADE,
#         related_name="payrolls"
#     )

#     month = models.PositiveSmallIntegerField()

#     year = models.PositiveSmallIntegerField()

#     gross_salary = models.DecimalField(
#         max_digits=10,
#         decimal_places=2
#     )

#     advance_deduction = models.DecimalField(
#         max_digits=10,
#         decimal_places=2,
#         default=0
#     )

#     net_salary = models.DecimalField(
#         max_digits=10,
#         decimal_places=2
#     )

#     status = models.CharField(
#         max_length=20,
#         choices=Status.choices,
#         default=Status.PENDING
#     )

#     payment_date = models.DateField(
#         null=True,
#         blank=True
#     )

#     remarks = models.TextField(
#         blank=True
#     )

#     created_at = models.DateTimeField(
#         auto_now_add=True
#     )

#     class Meta:
#         ordering = ["-year", "-month"]
#         unique_together = ("employee", "month", "year")

#     def __str__(self):
#         return f"{self.employee.name} - {self.month}/{self.year}"
