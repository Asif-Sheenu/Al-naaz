from django.conf import settings
from django.db import models
from organization.models import Branch




class FinancialAccount(models.Model):

    class AccountType(models.TextChoices):

        CASH = "CASH", "Cash"

        BANK = "BANK", "Bank"

        UPI = "UPI", "UPI"

        RECEIVABLE = "RECEIVABLE", "Receivable"

        PETTY_CASH = "PETTY_CASH", "Petty Cash"

    class AccountPurpose(models.TextChoices):

        GENERAL = "GENERAL", "General"

        CASH = "CASH", "Cash"

        UPI = "UPI", "UPI"

        CARD_RECEIVABLE = (
            "CARD_RECEIVABLE",
            "Card Receivable",
        )

        FOOD_DELIVERY_RECEIVABLE = (
            "FOOD_DELIVERY_RECEIVABLE",
            "Food Delivery Receivable",
        )   


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

    account_purpose = models.CharField(
        max_length=30,
        choices=AccountPurpose.choices,
        default=AccountPurpose.GENERAL,
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



class DeliveryPartner(models.Model):

    branch = models.ForeignKey(
        Branch,
        on_delete=models.PROTECT,
        related_name="delivery_partners",
    )

    name = models.CharField(
        max_length=100,
    )

    is_active = models.BooleanField(
        default=True,
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="created_delivery_partners",
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
                name="unique_del_partner_per_branch",
            ),
        ]

        indexes = [
            models.Index(
                fields=[
                    "branch",
                    "is_active",
                ],
                name="del_partner_branch_active_idx",
            ),
        ]

        ordering = [
            "name",
        ]

    def __str__(self):
        return (
            f"{self.branch.name} - "
            f"{self.name}"
        )


class DeliveryPartnerCommissionRate(models.Model):

    delivery_partner = models.ForeignKey(
        DeliveryPartner,
        on_delete=models.PROTECT,
        related_name="commission_rates",
    )

    commission_rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
    )

    effective_from = models.DateField()

    effective_to = models.DateField(
        null=True,
        blank=True,
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="created_delivery_partner_rates",
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    class Meta:

        constraints = [
            models.UniqueConstraint(
                fields=[
                    "delivery_partner",
                    "effective_from",
                ],
                name="unique_del_partner_rate_start",
            ),
        ]

        indexes = [
            models.Index(
                fields=[
                    "delivery_partner",
                    "effective_from",
                ],
                name="del_partner_rate_date_idx",
            ),
        ]

        ordering = [
            "-effective_from",
            "-id",
        ]

    def __str__(self):
        return (
            f"{self.delivery_partner.name} - "
            f"{self.commission_rate}% - "
            f"{self.effective_from}"
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

    transfer_group_id = models.UUIDField(
    null=True,
    blank=True,
    db_index=True,
    )

    idempotency_key = models.UUIDField(
        null=True,
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
        constraints = [
            models.UniqueConstraint(
                fields=["idempotency_key"],
                condition=models.Q(idempotency_key__isnull=False),
                name="unique_fin_tx_idempotency_key",
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

    branch = models.ForeignKey(
        Branch,
        on_delete=models.PROTECT,
        related_name="expenses",
        
    )

    category = models.ForeignKey(
        ExpenseCategory,
        on_delete=models.PROTECT,
        related_name="expenses"
    )

    payment_account = models.ForeignKey(
            FinancialAccount,
            on_delete=models.PROTECT,
            related_name="expenses",
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

    class Meta:
        indexes = [
            models.Index(
                fields=[
                    "branch",
                    "expense_date",
                ],
                name="expense_branch_date_idx",
            ),
        ]

    def __str__(self):
        return f"{self.branch.name} - {self.category.name} - {self.amount}"

    
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



class DailySales(models.Model):

    class Status(models.TextChoices):

        DRAFT = "DRAFT", "Draft"
        POSTED = "POSTED", "Posted"

    branch = models.ForeignKey(
        Branch,
        on_delete=models.PROTECT,
        related_name="daily_sales",
    )

    business_date = models.DateField()

    total_gross = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=0,
    )

    status = models.CharField(
        max_length=10,
        choices=Status.choices,
        default=Status.DRAFT,
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="created_daily_sales",
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
                    "business_date",
                ],
                name="unique_daily_sales_per_branch_date",
            )
        ]

        indexes = [
            models.Index(
                fields=[
                    "branch",
                    "business_date",
                ],
                name="daily_sales_branch_date_idx",
            ),
        ]

        ordering = [
            "-business_date",
            "-id",
        ]

    def __str__(self):
        return (
            f"{self.branch.name} - "
            f"{self.business_date} - "
            f"{self.total_gross}"
        )


class DailySalesPayment(models.Model):

    class PaymentMethod(models.TextChoices):

        CASH = "CASH", "Cash"

        UPI = "UPI", "UPI"

        CARD = "CARD", "Card"

        FOOD_DELIVERY = (
            "FOOD_DELIVERY",
            "Food Delivery",
        )

    daily_sales = models.ForeignKey(
        DailySales,
        on_delete=models.CASCADE,
        related_name="payments",
    )

    payment_method = models.CharField(
        max_length=20,
        choices=PaymentMethod.choices,
    )

    amount = models.DecimalField(
        max_digits=14,
        decimal_places=2,
    )

    delivery_partner = models.ForeignKey(
        DeliveryPartner,
        on_delete=models.PROTECT,
        related_name="daily_sales_payments",
        null=True,
        blank=True,
        )

    platform = models.CharField(
        max_length=100,
        blank=True,
    )


    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    class Meta:

        indexes = [
            models.Index(
                fields=[
                    "daily_sales",
                    "payment_method",
                ],
                name="daily_payment_sales_method_idx",
            ),
        ]

    def __str__(self):
        return (
            f"{self.payment_method} - "
            f"{self.amount}"
        )    



class Receivable(models.Model):

    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        PARTIALLY_SETTLED = "PARTIALLY_SETTLED", "Partially Settled"
        SETTLED = "SETTLED", "Settled"

    branch = models.ForeignKey(
        Branch,
        on_delete=models.PROTECT,
        related_name="receivables",
    )

    daily_sales_payment = models.OneToOneField(
    DailySalesPayment,
    on_delete=models.PROTECT,
    related_name="receivable",
   
    )
    
    receivable_account = models.ForeignKey(
        FinancialAccount,
        on_delete=models.PROTECT,
        related_name="receivable_records",
    )

    platform = models.CharField(
        max_length=100,
    )

    delivery_partner = models.ForeignKey(
        DeliveryPartner,
        on_delete=models.PROTECT,
        related_name="receivables",
        null=True,
        blank=True,
    )

    commission_rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
    )

    commission_amount = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        null=True,
        blank=True,
    )

    expected_net_amount = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        null=True,
        blank=True,
    )

    gross_amount = models.DecimalField(
        max_digits=14,
        decimal_places=2,
    )

    settled_amount = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=0,
    )

    outstanding_amount = models.DecimalField(
        max_digits=14,
        decimal_places=2,
    )

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
    )

    business_date = models.DateField()

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="created_receivables",
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:

        indexes = [
            models.Index(
                fields=[
                    "branch",
                    "status",
                    "business_date",
                ],
                name="recv_branch_status_date_idx",
            ),

            models.Index(
                fields=[
                    "receivable_account",
                    "status",
                ],
                name="recv_account_status_idx",
            ),
        ]

        ordering = [
            "-business_date",
            "-id",
        ]

    def __str__(self):
        return (
            f"{self.platform} - "
            f"{self.outstanding_amount}"
        )    



class ReceivableSettlement(models.Model):

    receivable = models.ForeignKey(
        Receivable,
        on_delete=models.PROTECT,
        related_name="settlements",
    )

    destination_account = models.ForeignKey(
        FinancialAccount,
        on_delete=models.PROTECT,
        related_name="receivable_settlements",
    )

    gross_amount = models.DecimalField(
        max_digits=14,
        decimal_places=2,
    )

    commission_amount = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=0,
    )

    received_amount = models.DecimalField(
        max_digits=14,
        decimal_places=2,
    )

    settlement_date = models.DateField()

    reference = models.CharField(
        max_length=100,
        blank=True,
    )

    description = models.CharField(
        max_length=255,
        blank=True,
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="created_receivable_settlements",
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    class Meta:
        indexes = [
            models.Index(
                fields=[
                    "receivable",
                    "settlement_date",
                ],
                name="recv_settle_date_idx",
            ),
            models.Index(
                fields=[
                    "destination_account",
                    "settlement_date",
                ],
                name="recv_settle_account_date_idx",
            ),
        ]

        ordering = [
            "-settlement_date",
            "-id",
        ]

    def __str__(self):
        return (
            f"Settlement #{self.id} - "
            f"{self.received_amount}"
        )    

class ExpenseAdjustment(models.Model):

    class Status(models.TextChoices):

        PENDING = "PENDING", "Pending"
        APPROVED = "APPROVED", "Approved"
        REJECTED = "REJECTED", "Rejected"

    expense = models.ForeignKey(
        Expense,
        on_delete=models.PROTECT,
        related_name="adjustments",
    )

    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="requested_expense_adjustments",
    )

    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="approved_expense_adjustments",
        null=True,
        blank=True,
    )

    rejected_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="rejected_expense_adjustments",
        null=True,
        blank=True,
        )

    status = models.CharField(
        max_length=10,
        choices=Status.choices,
        default=Status.PENDING,
    )

    # Existing values
    old_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
    )

    old_payment_account = models.ForeignKey(
        FinancialAccount,
        on_delete=models.PROTECT,
        related_name="old_expense_adjustments",
    )

    old_expense_date = models.DateField()

    old_category = models.ForeignKey(
        ExpenseCategory,
        on_delete=models.PROTECT,
        related_name="old_expense_adjustments",
    )

    old_description = models.TextField(
        blank=True,
    )

    # Requested new values
    new_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
    )

    new_payment_account = models.ForeignKey(
        FinancialAccount,
        on_delete=models.PROTECT,
        related_name="new_expense_adjustments",
    )

    new_expense_date = models.DateField()

    new_category = models.ForeignKey(
        ExpenseCategory,
        on_delete=models.PROTECT,
        related_name="new_expense_adjustments",
    )

    new_description = models.TextField(
        blank=True,
    )

    reason = models.TextField()

    rejection_reason = models.TextField(
        blank=True,
    )

    requested_at = models.DateTimeField(
        auto_now_add=True,
    )

    approved_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    rejected_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    class Meta:

        indexes = [
            models.Index(
                fields=[
                    "expense",
                    "status",
                ],
                name="expense_adj_expense_status_idx",
            ),

            models.Index(
                fields=[
                    "status",
                    "requested_at",
                ],
                name="expense_adj_status_date_idx",
            ),
        ]

        ordering = [
            "-requested_at",
            "-id",
        ]

    def __str__(self):
        return (
            f"Expense #{self.expense_id} - "
            f"{self.status}"
        )


class SupplierPayable(models.Model):

    class Status(models.TextChoices):
        OPEN = "OPEN", "Open"
        PARTIAL = "PARTIAL", "Partially Paid"
        PAID = "PAID", "Paid"

    purchase = models.OneToOneField(
        "inventory.Purchase",
        on_delete=models.PROTECT,
        related_name="payable"
    )

    supplier = models.ForeignKey(
        "inventory.Supplier",
        on_delete=models.PROTECT,
        related_name="payables"
    )

    branch = models.ForeignKey(
        "organization.Branch",
        on_delete=models.PROTECT,
        related_name="supplier_payables"
    )

    total_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2
    )

    paid_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0
    )

    outstanding_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2
    )

    status = models.CharField(
        max_length=10,
        choices=Status.choices,
        default=Status.OPEN
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    def __str__(self):
        return (
            f"Payable #{self.id} - "
            f"{self.supplier.name} - "
            f"{self.outstanding_amount}"
        )


class SupplierPayment(models.Model):

    payable = models.ForeignKey(
        SupplierPayable,
        on_delete=models.PROTECT,
        related_name="payments"
    )

    payment_account = models.ForeignKey(
        "expenses.FinancialAccount",
        on_delete=models.PROTECT,
        related_name="supplier_payments"
    )

    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2
    )

    payment_date = models.DateField()

    reference = models.CharField(
        max_length=100,
        blank=True
    )

    remarks = models.TextField(
        blank=True
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="supplier_payments_created",
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    def __str__(self):
        return (
            f"Supplier Payment #{self.id} - "
            f"{self.amount}"
        )        