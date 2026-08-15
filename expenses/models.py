from django.conf import settings
from django.db import models


class ExpenseCategory(models.Model):

    name = models.CharField(
        max_length=100,
        unique=True
    )

    is_active = models.BooleanField(
        default=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    def __str__(self):
        return self.name


class Expense(models.Model):

    category = models.ForeignKey(
        ExpenseCategory,
        on_delete=models.PROTECT,
        related_name="expenses"
    )

    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2
    )

    expense_date = models.DateField()

    description = models.TextField(
        blank=True
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="created_expenses"
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    def __str__(self):
        return f"{self.category.name} - {self.amount}"


class PettyCashLedger(models.Model):

    class TransactionType(models.TextChoices):

        OPENING = "OPENING", "Opening Balance"
        CASH_IN = "CASH_IN", "Cash Added"
        EXPENSE = "EXPENSE", "Expense"
        ADJUSTMENT = "ADJUSTMENT", "Adjustment"

    transaction_type = models.CharField(
        max_length=20,
        choices=TransactionType.choices
    )

    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2
    )

    balance_after = models.DecimalField(
        max_digits=12,
        decimal_places=2
    )

    transaction_date = models.DateField()

    expense = models.ForeignKey(
        Expense,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="cash_transactions"
    )

    remarks = models.TextField(
        blank=True
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="petty_cash_transactions"
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    class Meta:
        ordering = [
            "-transaction_date",
            "-id"
        ]

    def __str__(self):
        return (
            f"{self.transaction_type} - "
            f"{self.amount}"
        )