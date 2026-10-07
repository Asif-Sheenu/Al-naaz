from decimal import Decimal

from django.db import transaction
from rest_framework import serializers

from expenses.models import FinancialAccount
from expenses.services.supplier_payment_service import (
    process_supplier_purchase,
)

from .models import (
    Supplier,
    Product,
    Purchase,
    PurchaseItem,
    StockUsage,
    StockLedger,
    StockAdjustment,

)

from .services.purchase_service import process_purchase


# ============================================================
# SUPPLIER
# ============================================================

class SupplierSerializer(serializers.ModelSerializer):

    class Meta:
        model = Supplier

        fields = [
            "id",
            "name",
            "phone",
            "email",
            "address",
            "is_active",
            "created_at",
            "updated_at",
        ]

        read_only_fields = [
            "id",
            "created_at",
            "updated_at",
        ]


# ============================================================
# PRODUCT
# ============================================================

class ProductSerializer(serializers.ModelSerializer):

    class Meta:
        model = Product

        fields = [
            "id",
            "name",
            "category",
            "unit",
            "minimum_stock",
            "is_active",
            "created_at",
            "updated_at",
        ]

        read_only_fields = [
            "id",
            "created_at",
            "updated_at",
        ]

    def validate_minimum_stock(self, value):

        if value < 0:
            raise serializers.ValidationError(
                "Minimum stock cannot be negative."
            )

        return value


# ============================================================
# PURCHASE ITEM
# ============================================================

class PurchaseItemSerializer(serializers.ModelSerializer):

    product_name = serializers.CharField(
        source="product.name",
        read_only=True,
    )

    unit = serializers.CharField(
        source="product.unit",
        read_only=True,
    )

    class Meta:
        model = PurchaseItem

        fields = [
            "id",
            "product",
            "product_name",
            "unit",
            "quantity",
            "total_price",
            "unit_price",
        ]

        read_only_fields = [
            "id",
            "product_name",
            "unit",
            "unit_price",
        ]

    def validate_product(self, value):

        if not value.is_active:
            raise serializers.ValidationError(
                "This product is inactive."
            )

        return value

    def validate_quantity(self, value):

        if value <= 0:
            raise serializers.ValidationError(
                "Quantity must be greater than 0."
            )

        return value

    def validate_total_price(self, value):

        if value <= 0:
            raise serializers.ValidationError(
                "Total price must be greater than 0."
            )

        return value


# ============================================================
# INITIAL PAYMENT
# ============================================================

class InitialPaymentSerializer(serializers.Serializer):

    amount = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
        min_value=Decimal("0.01"),
    )

    payment_account = serializers.PrimaryKeyRelatedField(
        queryset=FinancialAccount.objects.filter(
            is_active=True
        )
    )


# ============================================================
# PURCHASE
# ============================================================

class PurchaseSerializer(serializers.ModelSerializer):

    supplier_name = serializers.CharField(
        source="supplier.name",
        read_only=True,
    )

    items = PurchaseItemSerializer(
        many=True
    )

    initial_payment = InitialPaymentSerializer(
        required=False
    )

    class Meta:
        model = Purchase

        fields = [
            "id",
            "branch",
            "supplier",
            "supplier_name",
            "purchase_date",
            "invoice_number",
            "remarks",
            "payment_status",
            "initial_payment",
            "items",
            "created_at",
        ]

        read_only_fields = [
            "id",
            "supplier_name",
            "payment_status",
            "created_at",
        ]

    # --------------------------------------------------------
    # Supplier validation
    # --------------------------------------------------------

    def validate_supplier(self, value):

        if not value.is_active:
            raise serializers.ValidationError(
                "This supplier is inactive."
            )

        return value

    # --------------------------------------------------------
    # Branch validation
    # --------------------------------------------------------

    def validate_branch(self, branch):

        request = self.context.get("request")

        if not request:
            return branch

        user = request.user

        if user.is_superuser or user.role == "ADMIN":
            return branch

        from organization.services.access_service import (
            get_accessible_branches,
        )

        accessible_branches = get_accessible_branches(user)

        if not accessible_branches.filter(
            id=branch.id
        ).exists():

            raise serializers.ValidationError(
                "You do not have access to this branch."
            )

        return branch

    # --------------------------------------------------------
    # Complete purchase validation
    # --------------------------------------------------------

    def validate(self, attrs):

        branch = attrs["branch"]
        items = attrs.get("items", [])
        initial_payment = attrs.get("initial_payment")

        if not items:
            raise serializers.ValidationError({
                "items": "At least one purchase item is required."
            })

        purchase_total = sum(
            (
                item["total_price"]
                for item in items
            ),
            Decimal("0"),
        )

        if purchase_total <= 0:
            raise serializers.ValidationError({
                "items": (
                    "Purchase total must be greater than zero."
                )
            })

        # ----------------------------------------------------
        # Initial payment validation
        # ----------------------------------------------------

        if initial_payment:

            payment_amount = initial_payment["amount"]

            if payment_amount > purchase_total:

                raise serializers.ValidationError({
                    "initial_payment": {
                        "amount": (
                            "Initial payment cannot be greater "
                            "than the purchase total."
                        )
                    }
                })

            payment_account = initial_payment[
                "payment_account"
            ]

            if payment_account.branch_id != branch.id:

                raise serializers.ValidationError({
                    "initial_payment": {
                        "payment_account": (
                            "Financial account does not belong "
                            "to the selected branch."
                        )
                    }
                })

        return attrs

    # --------------------------------------------------------
    # Create purchase
    # --------------------------------------------------------

    @transaction.atomic
    def create(self, validated_data):

        request = self.context.get("request")

        if not request:
            raise serializers.ValidationError(
                "Request context is required."
            )

        user = request.user

        items_data = validated_data.pop("items")
        initial_payment = validated_data.pop(
            "initial_payment",
            None,
        )

        # ----------------------------------------------------
        # Store creator
        # ----------------------------------------------------

        validated_data["created_by"] = user

        purchase = Purchase.objects.create(
            **validated_data
        )

        # ----------------------------------------------------
        # Create purchase items
        # ----------------------------------------------------

        for item_data in items_data:

            quantity = item_data["quantity"]
            total_price = item_data["total_price"]

            unit_price = (
                total_price / quantity
            )

            PurchaseItem.objects.create(
                purchase=purchase,
                product=item_data["product"],
                quantity=quantity,
                total_price=total_price,
                unit_price=unit_price,
            )

        # ----------------------------------------------------
        # Calculate total
        # ----------------------------------------------------

        purchase_total = sum(
            (
                item["total_price"]
                for item in items_data
            ),
            Decimal("0"),
        )

        # ----------------------------------------------------
        # Update stock
        #
        # process_purchase now:
        # StockBalance + StockLedger
        # ----------------------------------------------------

        process_purchase(purchase)

        # ----------------------------------------------------
        # Supplier payable + initial payment
        #
        # KEEPING EXISTING FINANCE FLOW
        # ----------------------------------------------------

        process_supplier_purchase(
            purchase=purchase,
            total_amount=purchase_total,
            initial_payment=initial_payment,
            created_by=user,
        )

        return purchase


# ============================================================
# STOCK USAGE
# ============================================================

class StockUsageSerializer(serializers.ModelSerializer):

    class Meta:
        model = StockUsage

        fields = [
            "id",
            "branch",
            "product",
            "quantity",
            "usage_date",
            "remarks",
            "created_at",
        ]

        read_only_fields = [
            "id",
            "created_at",
        ]

    # --------------------------------------------------------
    # Branch validation
    # --------------------------------------------------------

    def validate_branch(self, branch):

        request = self.context.get("request")

        if not request:
            return branch

        user = request.user

        if user.is_superuser or user.role == "ADMIN":
            return branch

        from organization.services.access_service import (
            get_accessible_branches,
        )

        accessible_branches = get_accessible_branches(user)

        if not accessible_branches.filter(
            id=branch.id
        ).exists():

            raise serializers.ValidationError(
                "You do not have access to this branch."
            )

        return branch

    # --------------------------------------------------------
    # Product validation
    # --------------------------------------------------------

    def validate_product(self, product):

        if not product.is_active:
            raise serializers.ValidationError(
                "This product is inactive."
            )

        return product

    # --------------------------------------------------------
    # Quantity validation
    # --------------------------------------------------------

    def validate_quantity(self, value):

        if value <= 0:
            raise serializers.ValidationError(
                "Usage quantity must be greater than zero."
            )

        return value

    # --------------------------------------------------------
    # Store created_by
    # --------------------------------------------------------

    def create(self, validated_data):

        request = self.context.get("request")

        if request:
            validated_data["created_by"] = request.user

        return super().create(validated_data)




# ============================================================
# STOCK ADJUSTMENT
# ============================================================

class StockAdjustmentSerializer(serializers.ModelSerializer):

    class Meta:
        model = StockAdjustment

        fields = [
            "id",
            "branch",
            "product",
            "adjustment_type",
            "quantity",
            "adjustment_date",
            "reason",
            "created_by",
            "created_at",
        ]

        read_only_fields = [
            "id",
            "created_by",
            "created_at",
        ]

    # --------------------------------------------------------
    # Branch validation
    # --------------------------------------------------------

    def validate_branch(self, branch):

        request = self.context.get("request")

        if not request:
            return branch

        user = request.user

        # ADMIN / superuser can use any branch
        if user.is_superuser or user.role == "ADMIN":
            return branch

        from organization.services.access_service import (
            get_accessible_branches,
        )

        accessible_branches = get_accessible_branches(user)

        if not accessible_branches.filter(
            id=branch.id
        ).exists():

            raise serializers.ValidationError(
                "You do not have access to this branch."
            )

        return branch

    # --------------------------------------------------------
    # Product validation
    # --------------------------------------------------------

    def validate_product(self, product):

        if not product.is_active:
            raise serializers.ValidationError(
                "This product is inactive."
            )

        return product

    # --------------------------------------------------------
    # Quantity validation
    # --------------------------------------------------------

    def validate_quantity(self, value):

        if value <= 0:
            raise serializers.ValidationError(
                "Adjustment quantity must be greater than zero."
            )

        return value

    # --------------------------------------------------------
    # Reason validation
    # --------------------------------------------------------

    def validate_reason(self, value):

        if not value or not value.strip():
            raise serializers.ValidationError(
                "Reason is required."
            )

        return value.strip()

    # --------------------------------------------------------
    # Store created_by
    # --------------------------------------------------------

    def create(self, validated_data):

        request = self.context.get("request")

        if request:
            validated_data["created_by"] = request.user

        return super().create(validated_data)
    
# ============================================================
# LIVE STOCK
# ============================================================

class StockSerializer(serializers.Serializer):

    product = serializers.IntegerField()

    product_name = serializers.CharField()

    unit = serializers.CharField()

    current_stock = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
    )

    minimum_stock = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
    )

    status = serializers.CharField()


# ============================================================
# STOCK LEDGER
# ============================================================

class StockLedgerSerializer(serializers.ModelSerializer):

    product_name = serializers.CharField(
        source="product.name",
        read_only=True,
    )

    unit = serializers.CharField(
        source="product.unit",
        read_only=True,
    )

    supplier_name = serializers.SerializerMethodField()

    total_price = serializers.SerializerMethodField()

    unit_price = serializers.SerializerMethodField()

    class Meta:
        model = StockLedger

        fields = [
            "id",
            "branch",
            "product",
            "product_name",
            "unit",
            "movement_type",
            "quantity",
            "balance_before",
            "balance_after",
            "movement_date",
            "reference_type",
            "reference_id",
            "remarks",
            "created_by",
            "supplier_name",
            "total_price",
            "unit_price",
            "created_at",
        ]

        read_only_fields = fields

    # --------------------------------------------------------
    # Supplier
    # --------------------------------------------------------

    def get_supplier_name(self, obj):

        if (
            obj.reference_type
            != StockLedger.ReferenceType.PURCHASE
        ):
            return None

        if not obj.reference_id:
            return None

        try:

            purchase = (
                Purchase.objects
                .select_related("supplier")
                .get(
                    id=obj.reference_id
                )
            )

            return purchase.supplier.name

        except Purchase.DoesNotExist:

            return None

    # --------------------------------------------------------
    # Total price
    # --------------------------------------------------------

    def get_total_price(self, obj):

        if (
            obj.reference_type
            != StockLedger.ReferenceType.PURCHASE
        ):
            return None

        if not obj.reference_id:
            return None

        try:

            purchase = (
                Purchase.objects
                .get(
                    id=obj.reference_id
                )
            )

            purchase_item = (
                PurchaseItem.objects
                .filter(
                    purchase=purchase,
                    product=obj.product,
                )
                .first()
            )

            if purchase_item:
                return purchase_item.total_price

        except Purchase.DoesNotExist:

            pass

        return None

    # --------------------------------------------------------
    # Unit price
    # --------------------------------------------------------

    def get_unit_price(self, obj):

        if (
            obj.reference_type
            != StockLedger.ReferenceType.PURCHASE
        ):
            return None

        if not obj.reference_id:
            return None

        try:

            purchase = (
                Purchase.objects
                .get(
                    id=obj.reference_id
                )
            )

            purchase_item = (
                PurchaseItem.objects
                .filter(
                    purchase=purchase,
                    product=obj.product,
                )
                .first()
            )

            if purchase_item:
                return purchase_item.unit_price

        except Purchase.DoesNotExist:

            pass

        return None


# ============================================================
# SUPPLIER PURCHASE HISTORY
# ============================================================

class SupplierPurchaseHistorySerializer(
    serializers.ModelSerializer
):

    supplier_name = serializers.CharField(
        source="purchase.supplier.name",
        read_only=True,
    )

    purchase_date = serializers.DateField(
        source="purchase.purchase_date",
        read_only=True,
    )

    invoice_number = serializers.CharField(
        source="purchase.invoice_number",
        read_only=True,
    )

    product_name = serializers.CharField(
        source="product.name",
        read_only=True,
    )

    unit = serializers.CharField(
        source="product.unit",
        read_only=True,
    )

    class Meta:
        model = PurchaseItem

        fields = [
            "id",
            "purchase",
            "supplier_name",
            "purchase_date",
            "invoice_number",
            "product",
            "product_name",
            "unit",
            "quantity",
            "total_price",
            "unit_price",
        ]

        read_only_fields = fields