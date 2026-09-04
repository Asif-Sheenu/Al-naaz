from django.db import models

from organization.models import Branch,Department


class Employee(models.Model):

    class SalaryType(models.TextChoices):
        MONTHLY = "MONTHLY", "Monthly"
        DAILY = "DAILY", "Daily"
        BIWEEKLY = "BIWEEKLY", "15 Days"

    branch = models.ForeignKey(
        Branch,
        on_delete=models.PROTECT,
        related_name="employees",

    )

    name = models.CharField(
        max_length=100
    )

    phone = models.CharField(
        max_length=15
    )

    address = models.TextField(
        blank=True
    )

    department = models.ForeignKey(
    Department,
    on_delete=models.PROTECT,
    related_name="employees",
    null=True,
    blank=True,
    )

    designation = models.CharField(
        max_length=100
    )

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

    is_active = models.BooleanField(
        default=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    def __str__(self):
        return self.name




    # ----------------------------------------------------------------------------------------------- 
    # 

class EmployeeIdentityProof(models.Model):

    class DocumentType(models.TextChoices):
        AADHAAR = "AADHAAR", "Aadhaar"
        PAN = "PAN", "PAN"
        DRIVING_LICENSE = "DRIVING_LICENSE", "Driving License"
        PASSPORT = "PASSPORT", "Passport"
        OTHER = "OTHER", "Other"

    employee = models.OneToOneField(
        Employee,
        on_delete=models.PROTECT,
        related_name="identity_proof",
    )

    document_type = models.CharField(
        max_length=30,
        choices=DocumentType.choices,
    )

    document_number = models.CharField(
        max_length=100,
    )

    cloudinary_public_id = models.CharField(
        max_length=500,
        unique=True,
    )
    cloudinary_resource_type = models.CharField(
    max_length=20,
    default="image",
    )

    original_filename = models.CharField(
        max_length=255,
    )

    mime_type = models.CharField(
        max_length=100,
    )

    file_size = models.PositiveBigIntegerField()

    uploaded_by = models.ForeignKey(
        "users.User",
        on_delete=models.PROTECT,
        related_name="uploaded_identity_proofs",
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    def __str__(self):
        return (
            f"{self.employee.name} - "
            f"{self.get_document_type_display()}"
        )        




    #  ------------------------------------------------------------------------------------------------------------- 
    # 

class EmployeeSalaryHistory(models.Model):

    employee = models.ForeignKey(
        Employee,
        on_delete=models.PROTECT,
        related_name="salary_history",
    )

    salary_type = models.CharField(
        max_length=20,
        choices=Employee.SalaryType.choices,
    )

    monthly_salary = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
    )

    daily_wage = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
    )

    biweekly_salary = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
    )

    effective_from = models.DateField()

    effective_to = models.DateField(
        null=True,
        blank=True,
    )

    reason = models.CharField(
        max_length=255,
        blank=True,
    )

    created_by = models.ForeignKey(
        "users.User",
        on_delete=models.PROTECT,
        related_name="salary_changes",
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    class Meta:
        ordering = ["-effective_from"]

    def __str__(self):
        return (
            f"{self.employee.name} - "
            f"{self.effective_from}"
        )   