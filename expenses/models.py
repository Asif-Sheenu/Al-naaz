from django.conf import settings
from django.db import models
from organization.models import Branch




class FinancialAccount(models.Model):

    class AccountType(models.TextChoices):

        CASH = "CASH", "Cash"

        BANK = "BANK", "Bank"

        UPI = "UPI", "UPI"

        PETTY_CASH = "PETTY_CASH", "Petty Cash"

    branch = models.ForeignKey(
        Branch,
        on_delete=models.PROTECT,
        related_name="financial_accounts",
    )

    name = models.CharField(
        max_length=100,
    )

    account_type = models.CharField(
        max_length=20,
        choices=AccountType.choices,
    )

    opening_balance = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=0,
    )
    opening_balance_date = models.DateField(null=True,
    blank=True,)

    is_active = models.BooleanField(
        default=True,
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="created_financial_accounts",
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:

        constraints = [
            models.UniqueConstraint(
                fields=[
                    "branch",
                    "name",
                ],
                name="unique_financial_account_per_branch",
            )
        ]

        indexes = [
            models.Index(
                fields=[
                    "branch",
                    "account_type",
                ],
                name="fin_acct_branch_type_idx",
            ),
        ]

    def __str__(self):
        return (
            f"{self.branch.name} - "
            f"{self.name}"
        )



class FinancialTransaction(models.Model):

    class TransactionType(models.TextChoices):

        OPENING_BALANCE = (
            "OPENING_BALANCE",
            "Opening Balance",
        )

        REVENUE = (
            "REVENUE",
            "Revenue",
        )

        EXPENSE = (
            "EXPENSE",
            "Expense",
        )

        SUPPLIER_PAYMENT = (
            "SUPPLIER_PAYMENT",
            "Supplier Payment",
        )

        ASSET_PURCHASE = (
            "ASSET_PURCHASE",
            "Asset Purchase",
        )

        TRANSFER_IN = (
            "TRANSFER_IN",
            "Transfer In",
        )

        TRANSFER_OUT = (
            "TRANSFER_OUT",
            "Transfer Out",
        )

        ADJUSTMENT = (
            "ADJUSTMENT",
            "Adjustment",
        )

    class Direction(models.TextChoices):

        IN = "IN", "Money In"

        OUT = "OUT", "Money Out"

    branch = models.ForeignKey(
        Branch,
        on_delete=models.PROTECT,
        related_name="financial_transactions",
    )

    account = models.ForeignKey(
        FinancialAccount,
        on_delete=models.PROTECT,
        related_name="transactions",
    )

    transaction_type = models.CharField(
        max_length=30,
        choices=TransactionType.choices,
    )

    direction = models.CharField(
        max_length=10,
        choices=Direction.choices,
    )

    amount = models.DecimalField(
        max_digits=14,
        decimal_places=2,
    )

    transaction_date = models.DateField()

    description = models.TextField(
        blank=True,
    )

    reference = models.CharField(
        max_length=100,
        blank=True,
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="created_financial_transactions",
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    class Meta:

        ordering = [
            "-transaction_date",
            "-id",
        ]

        indexes = [
            models.Index(
                fields=[
                    "branch",
                    "transaction_date",
                ],
                name="fin_tx_branch_date_idx",
            ),

            models.Index(
                fields=[
                    "account",
                    "transaction_date",
                ],
                name="fin_tx_account_date_idx",
            ),

            models.Index(
                fields=[
                    "transaction_type",
                    "transaction_date",
                ],
                name="fin_tx_type_date_idx",
            ),
        ]

    def __str__(self):
        return (
            f"{self.transaction_type} - "
            f"{self.direction} - "
            f"{self.amount}"
        )



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