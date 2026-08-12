from django.db import models


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

# ---------------------------------------------------------------------------------------

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



# -------------------------------------------------------------------------------


class Purchase(models.Model):

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

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    def __str__(self):
        return f"Purchase #{self.id} - {self.supplier.name}"


# =----------------------------------------------------------------------------------- 
# 

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


    def __str__(self):
        return f"{self.product.name} - {self.quantity}"  

    # --------------------------------------------------------------------------------- 
    

class StockUsage(models.Model):

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

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    def __str__(self):
        return f"{self.product.name} - {self.quantity}"



# ------------------------------------------------------------------------------------------
# 

class StockLedger(models.Model):

    class MovementType(models.TextChoices):
        PURCHASE = "PURCHASE", "Purchase"
        USAGE = "USAGE", "Usage"
        ADJUSTMENT = "ADJUSTMENT", "Adjustment"

    product = models.ForeignKey(
        Product,
        on_delete=models.PROTECT,
        related_name="ledger_entries"
    )

    movement_type = models.CharField(
        max_length=20,
        choices=MovementType.choices
    )

    quantity = models.DecimalField(
        max_digits=10,
        decimal_places=2
    )

    balance_after = models.DecimalField(
        max_digits=10,
        decimal_places=2
    )

    reference_id = models.PositiveIntegerField(
        null=True,
        blank=True
    )

    movement_date = models.DateField()

    remarks = models.TextField(
        blank=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    class Meta:
        ordering = ["-movement_date", "-id"]

    def __str__(self):
        return (
            f"{self.product.name} - "
            f"{self.movement_type} - "
            f"{self.quantity}"
        )        

