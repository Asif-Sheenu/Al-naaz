from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone
from decimal import Decimal


class IssuedItem(models.Model):

    class ApprovalStatus(models.TextChoices):
        PENDING_MANAGER = "PENDING_MANAGER", "Pending Manager Approval"
        PENDING_ADMIN = "PENDING_ADMIN", "Pending Admin Approval"
        APPROVED = "APPROVED", "Approved"
        REJECTED = "REJECTED", "Rejected"
        CANCELLED = "CANCELLED", "Cancelled"

    employee = models.ForeignKey(
        "employees.Employee",
        on_delete=models.PROTECT,
        related_name="clearance_items",
    )

    item_name = models.CharField(max_length=150)

    quantity = models.PositiveIntegerField(
        validators=[MinValueValidator(1)],
    )

    unit_value = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        help_text="Value of one item.",
    )

    employee_payable = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        help_text="Total amount the employee is required to pay.",
    )

    issued_date = models.DateField(default=timezone.localdate)

    issued_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="clearance_items_issued",
    )

    approval_status = models.CharField(
        max_length=20,
        choices=ApprovalStatus.choices,
        default=ApprovalStatus.PENDING_MANAGER,
        db_index=True,
    )

    manager_approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="clearance_items_manager_approved",
    )

    manager_approved_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    admin_approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="clearance_items_admin_approved",
    )

    admin_approved_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    rejection_reason = models.TextField(blank=True)

    notes = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-issued_date", "-id"]
        indexes = [
            models.Index(
                fields=["employee", "approval_status"],
                name="clear_emp_approval_idx",
            ),
            models.Index(
                fields=["issued_date"],
                name="clear_issued_date_idx",
            ),
        ]

    def __str__(self):
        return f"{self.employee.name} - {self.item_name}"


class ClearancePayment(models.Model):

    class PaymentMethod(models.TextChoices):
        CASH = "CASH", "Cash"
        UPI = "UPI", "UPI"
        BANK_TRANSFER = "BANK_TRANSFER", "Bank Transfer"
        OTHER = "OTHER", "Other"

    issued_item = models.ForeignKey(
        IssuedItem,
        on_delete=models.PROTECT,
        related_name="payments",
    )

    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.01"))],
    )

    payment_method = models.CharField(
        max_length=20,
        choices=PaymentMethod.choices,
        default=PaymentMethod.CASH,
    )

    payment_date = models.DateField(default=timezone.localdate)

    recorded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="clearance_payments_recorded",
    )

    reference = models.CharField(max_length=100, blank=True)

    notes = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-payment_date", "-id"]
        indexes = [
            models.Index(
                fields=["issued_item", "payment_date"],
                name="clear_pay_item_date_idx",
            ),
        ]

    def __str__(self):
        return (
            f"{self.issued_item.employee.name} - "
            f"{self.amount}"
        )