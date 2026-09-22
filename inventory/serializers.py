from rest_framework import serializers
from .services.purchase_service import process_purchase
from .models import Supplier, Product, Purchase,PurchaseItem, StockUsage,StockLedger
from django.db import transaction
from expenses.models import FinancialAccount
from expenses.services.supplier_payment_service import process_supplier_purchase
from decimal import Decimal


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


class PurchaseItemSerializer(serializers.ModelSerializer):

    product_name = serializers.CharField(
        source="product.name",
        read_only=True
    )

    unit = serializers.CharField(
        source="product.unit",
        read_only=True
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


class InitialPaymentSerializer(serializers.Serializer):

    amount = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
        min_value=Decimal("0.01")
    )

    payment_account = serializers.PrimaryKeyRelatedField(
        queryset=FinancialAccount.objects.filter(
            is_active=True
        )
    )


class PurchaseSerializer(serializers.ModelSerializer):

    supplier_name = serializers.CharField(
        source="supplier.name",
        read_only=True
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

    def validate_supplier(self, value):

        if not value.is_active:
            raise serializers.ValidationError(
                "This supplier is inactive."
            )

        return value

    def validate(self, attrs):

        branch = attrs["branch"]
        initial_payment = attrs.get("initial_payment")

        # Calculate purchase total
        items = attrs.get("items", [])

        purchase_total = sum(
            item["total_price"]
            for item in items
        )

        if purchase_total <= 0:
            raise serializers.ValidationError({
                "items": "Purchase total must be greater than zero."
            })

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

    @transaction.atomic
    def create(self, validated_data):
        items_data = validated_data.pop("items")
        initial_payment = validated_data.pop("initial_payment", None)

        purchase = Purchase.objects.create(**validated_data)

        for item_data in items_data:
            quantity = item_data["quantity"]
            total_price = item_data["total_price"]

            unit_price = total_price / quantity

            PurchaseItem.objects.create(
                purchase=purchase,
                product=item_data["product"],
                quantity=quantity,
                total_price=total_price,
                unit_price=unit_price,
            )

        # Calculate complete purchase amount
        purchase_total = sum(
            item["total_price"]
            for item in items_data
        )

        # Add stock
        process_purchase(purchase)

        # Create payable + process initial payment
        process_supplier_purchase(
            purchase=purchase,
            total_amount=purchase_total,
            initial_payment=initial_payment,
            created_by=self.context["request"].user,
        )

        return purchase
# ---------------------------------

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

    def validate_quantity(self, value):
        if value <= 0:
            raise serializers.ValidationError(
                "Usage quantity must be greater than 0."
            )

        return value

        # live stock ----------------------------------------------   


class StockSerializer(serializers.Serializer):

    product = serializers.IntegerField()
    product_name = serializers.CharField()
    unit = serializers.CharField()
    current_stock = serializers.DecimalField(
        max_digits=10,
        decimal_places=2
    )
    minimum_stock = serializers.DecimalField(
        max_digits=10,
        decimal_places=2
    )
    status = serializers.CharField()        




    # ------------------------------------------------------------------------------------------------------  

    

class StockLedgerSerializer(serializers.ModelSerializer):

    product_name = serializers.CharField(
        source="product.name",
        read_only=True
    )

    unit = serializers.CharField(
        source="product.unit",
        read_only=True
    )

    supplier_name = serializers.SerializerMethodField()
    total_price = serializers.SerializerMethodField()
    unit_price = serializers.SerializerMethodField()

    class Meta:
        model = StockLedger

        fields = [
            "id",
            "product",
            "product_name",
            "unit",
            "movement_type",
            "quantity",
            "balance_after",
            "movement_date",
            "reference_id",
            "remarks",
            "supplier_name",
            "total_price",
            "unit_price",
        ]

        read_only_fields = fields

    def get_supplier_name(self, obj):

        if obj.movement_type != "PURCHASE":
            return None

        try:
            purchase_item = PurchaseItem.objects.select_related(
                "purchase__supplier"
            ).get(
                id=obj.reference_id
            )

            return purchase_item.purchase.supplier.name

        except PurchaseItem.DoesNotExist:
            return None

    def get_total_price(self, obj):

        if obj.movement_type != "PURCHASE":
            return None

        try:
            purchase_item = PurchaseItem.objects.get(
                id=obj.reference_id
            )

            return purchase_item.total_price

        except PurchaseItem.DoesNotExist:
            return None

    def get_unit_price(self, obj):

        if obj.movement_type != "PURCHASE":
            return None

        try:
            purchase_item = PurchaseItem.objects.get(
                id=obj.reference_id
            )

            return purchase_item.unit_price

        except PurchaseItem.DoesNotExist:
            return None





            # ------------------------------------------------------------------------------------------


class SupplierPurchaseHistorySerializer(serializers.ModelSerializer):

    supplier_name = serializers.CharField(
        source="purchase.supplier.name",
        read_only=True
    )

    purchase_date = serializers.DateField(
        source="purchase.purchase_date",
        read_only=True
    )

    invoice_number = serializers.CharField(
        source="purchase.invoice_number",
        read_only=True
    )

    product_name = serializers.CharField(
        source="product.name",
        read_only=True
    )

    unit = serializers.CharField(
        source="product.unit",
        read_only=True
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


        