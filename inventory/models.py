from django.db import models


# =============================================================================
# IDEMPOTENCY
# =============================================================================

class IdempotencyRecord(models.Model):

    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        COMPLETED = "COMPLETED", "Completed"

    # Client sends this through:
    # Idempotency-Key: <unique-key>
    key = models.CharField(
        max_length=255,
        unique=True
    )

    # Example:
    # inventory.purchase.create
    # inventory.stock_usage.create
    # inventory.stock_adjustment.create
    operation = models.CharField(
        max_length=100
    )

    # SHA-256 hash of the request payload.
    # Prevents the same key being reused with different data.
    request_hash = models.CharField(
        max_length=64
    )

    user = models.ForeignKey(
        "users.User",
        on_delete=models.PROTECT,
        related_name="inventory_idempotency_records"
    )

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING
    )

    # Resource created by the request.
    #
    # Example:
    # resource_type = "Purchase"
    # resource_id = 101
    resource_type = models.CharField(
        max_length=100,
        blank=True
    )

    resource_id = models.PositiveIntegerField(
        null=True,
        blank=True
    )

    response_status_code = models.PositiveSmallIntegerField(
        null=True,
        blank=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    completed_at = models.DateTimeField(
        null=True,
        blank=True
    )

    expires_at = models.DateTimeField(
        null=True,
        blank=True
    )

    class Meta:
        indexes = [
            models.Index(
                fields=["user", "operation", "created_at"]
            ),
            models.Index(
                fields=["expires_at"]
            ),
        ]

    def __str__(self):
        return f"{self.operation} - {self.key}"


# =============================================================================
# SUPPLIER
# =============================================================================

class Supplier(models.Model):

    name = models.CharField(
        max_length=150,
        unique=True
    )

    phone = models.CharField(
        max_length=20,
        blank=True
    )

    email = models.EmailField(
        blank=True
    )

    address = models.TextField(
        blank=True
    )

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


# =============================================================================
# PRODUCT
# =============================================================================

class Product(models.Model):

    class Unit(models.TextChoices):
        KG = "KG", "Kilogram"
        LITRE = "LITRE", "Litre"
        PIECE = "PIECE", "Piece"
        PACKET = "PACKET", "Packet"
        BOX = "BOX", "Box"
        BOTTLE = "BOTTLE", "Bottle"

    name = models.CharField(
        max_length=100,
        unique=True
    )

    category = models.CharField(
        max_length=100,
        blank=True
    )

    unit = models.CharField(
        max_length=20,
        choices=Unit.choices
    )

    minimum_stock = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0
    )

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
        return f"{self.name} ({self.unit})"


# =============================================================================
# PURCHASE
# =============================================================================

class Purchase(models.Model):

    class PaymentStatus(models.TextChoices):
        CREDIT = "CREDIT", "Credit"
        PARTIAL = "PARTIAL", "Partially Paid"
        PAID = "PAID", "Paid"

    branch = models.ForeignKey(
        "organization.Branch",
        on_delete=models.PROTECT,
        related_name="purchases"
    )

    supplier = models.ForeignKey(
        Supplier,
        on_delete=models.PROTECT,
        related_name="purchases"
    )

    purchase_date = models.DateField()

    invoice_number = models.CharField(
        max_length=100,
        blank=True
    )

    remarks = models.TextField(
        blank=True
    )

    payment_status = models.CharField(
        max_length=10,
        choices=PaymentStatus.choices,
        default=PaymentStatus.CREDIT
    )

    created_by = models.ForeignKey(
        "users.User",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="purchases_created"
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    class Meta:
        indexes = [
            models.Index(
                fields=["branch", "purchase_date"]
            ),
            models.Index(
                fields=["supplier", "purchase_date"]
            ),
        ]

    def __str__(self):
        return f"Purchase #{self.id} - {self.supplier.name}"


# =============================================================================
# PURCHASE ITEM
# =============================================================================

class PurchaseItem(models.Model):

    purchase = models.ForeignKey(
        Purchase,
        on_delete=models.CASCADE,
        related_name="items"
    )

    product = models.ForeignKey(
        Product,
        on_delete=models.PROTECT,
        related_name="purchase_items"
    )

    quantity = models.DecimalField(
        max_digits=10,
        decimal_places=2
    )

    total_price = models.DecimalField(
        max_digits=12,
        decimal_places=2
    )

    unit_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        editable=False
    )

    class Meta:
        indexes = [
            models.Index(
                fields=["purchase", "product"]
            ),
        ]

    def __str__(self):
        return f"{self.product.name} - {self.quantity}"


# =============================================================================
# STOCK USAGE
# =============================================================================

class StockUsage(models.Model):

    branch = models.ForeignKey(
        "organization.Branch",
        on_delete=models.PROTECT,
        related_name="stock_usages"
    )

    product = models.ForeignKey(
        Product,
        on_delete=models.PROTECT,
        related_name="usages"
    )

    quantity = models.DecimalField(
        max_digits=10,
        decimal_places=2
    )

    usage_date = models.DateField()

    remarks = models.TextField(
        blank=True
    )

    created_by = models.ForeignKey(
        "users.User",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="stock_usages_created"
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    class Meta:
        indexes = [
            models.Index(
                fields=["branch", "usage_date"]
            ),
            models.Index(
                fields=["product", "usage_date"]
            ),
        ]

    def __str__(self):
        return f"{self.product.name} - {self.quantity}"


# =============================================================================
# STOCK BALANCE
# =============================================================================

class StockBalance(models.Model):

    branch = models.ForeignKey(
        "organization.Branch",
        on_delete=models.PROTECT,
        related_name="stock_balances"
    )

    product = models.ForeignKey(
        Product,
        on_delete=models.PROTECT,
        related_name="stock_balances"
    )

    quantity = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["branch", "product"],
                name="unique_stock_balance_branch_product"
            ),

            models.CheckConstraint(
                condition=models.Q(quantity__gte=0),
                name="stock_balance_quantity_non_negative"
            ),
        ]

        indexes = [
            models.Index(
                fields=["product"]
            ),
        ]

    def __str__(self):
        return (
            f"{self.branch} - "
            f"{self.product} - "
            f"{self.quantity}"
        )


# =============================================================================
# STOCK ADJUSTMENT
# =============================================================================

class StockAdjustment(models.Model):

    class AdjustmentType(models.TextChoices):
        INCREASE = "INCREASE", "Increase"
        DECREASE = "DECREASE", "Decrease"

    branch = models.ForeignKey(
        "organization.Branch",
        on_delete=models.PROTECT,
        related_name="stock_adjustments"
    )

    product = models.ForeignKey(
        Product,
        on_delete=models.PROTECT,
        related_name="stock_adjustments"
    )

    adjustment_type = models.CharField(
        max_length=10,
        choices=AdjustmentType.choices
    )

    quantity = models.DecimalField(
        max_digits=12,
        decimal_places=2
    )

    adjustment_date = models.DateField()

    reason = models.TextField()

    created_by = models.ForeignKey(
        "users.User",
        on_delete=models.PROTECT,
        related_name="stock_adjustments_created"
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    class Meta:
        ordering = ["-created_at", "-id"]

        indexes = [
            models.Index(
                fields=["branch", "product"]
            ),
            models.Index(
                fields=["adjustment_date"]
            ),
        ]

        constraints = [
            models.CheckConstraint(
                condition=models.Q(quantity__gt=0),
                name="stock_adjustment_quantity_positive"
            ),
        ]

    def __str__(self):
        return (
            f"Adjustment #{self.id} - "
            f"{self.product.name} - "
            f"{self.quantity}"
        )


# =============================================================================
# STOCK LEDGER
# =============================================================================

class StockLedger(models.Model):

    class MovementType(models.TextChoices):
        PURCHASE = "PURCHASE", "Purchase"
        USAGE = "USAGE", "Usage"
        ADJUSTMENT = "ADJUSTMENT", "Adjustment"

    class ReferenceType(models.TextChoices):
        PURCHASE = "PURCHASE", "Purchase"
        STOCK_USAGE = "STOCK_USAGE", "Stock Usage"
        STOCK_ADJUSTMENT = "STOCK_ADJUSTMENT", "Stock Adjustment"

    branch = models.ForeignKey(
        "organization.Branch",
        on_delete=models.PROTECT,
        related_name="stock_ledger_entries"
    )

    product = models.ForeignKey(
        Product,
        on_delete=models.PROTECT,
        related_name="ledger_entries"
    )

    movement_type = models.CharField(
        max_length=20,
        choices=MovementType.choices
    )

    # Signed stock movement:
    #
    # PURCHASE   -> +quantity
    # USAGE      -> -quantity
    # ADJUSTMENT -> positive or negative
    quantity = models.DecimalField(
        max_digits=12,
        decimal_places=2
    )

    # Stock immediately before this movement.
    balance_before = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True
    )

    # Stock immediately after this movement.
    balance_after = models.DecimalField(
        max_digits=12,
        decimal_places=2
    )

    # Kept for compatibility with existing ledger records.
    reference_type = models.CharField(
        max_length=30,
        blank=True
    )

    reference_id = models.PositiveIntegerField(
        null=True,
        blank=True
    )

    movement_date = models.DateField()

    remarks = models.TextField(
        blank=True
    )

    created_by = models.ForeignKey(
        "users.User",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="stock_ledger_entries_created"
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    class Meta:
        ordering = ["-movement_date", "-id"]

        indexes = [
            models.Index(
                fields=[
                    "branch",
                    "product",
                    "movement_date"
                ]
            ),
            models.Index(
                fields=[
                    "movement_type",
                    "movement_date"
                ]
            ),
            models.Index(
                fields=[
                    "reference_type",
                    "reference_id"
                ]
            ),
        ]

    def __str__(self):
        return (
            f"{self.product.name} - "
            f"{self.movement_type} - "
            f"{self.quantity}"
        )