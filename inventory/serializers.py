from rest_framework import serializers
from .services.purchase_service import process_purchase
from .models import Supplier, Product, Purchase,PurchaseItem, StockUsage,StockLedger
from django.db import transaction

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

class PurchaseSerializer(serializers.ModelSerializer):

    supplier_name = serializers.CharField(
        source="supplier.name",
        read_only=True
    )

    items = PurchaseItemSerializer(
        many=True
    )

    class Meta:
        model = Purchase

        fields = [
            "id",
            "supplier",
            "supplier_name",
            "purchase_date",
            "invoice_number",
            "remarks",
            "items",
            "created_at",
        ]

        read_only_fields = [
            "id",
            "supplier_name",
            "created_at",
        ]

    def validate_supplier(self, value):

        if not value.is_active:
            raise serializers.ValidationError(
                "This supplier is inactive."
            )

        return value

    @transaction.atomic
    def create(self, validated_data):

        items_data = validated_data.pop("items")

        purchase = Purchase.objects.create(
            **validated_data
        )

        for item_data in items_data:

            quantity = item_data["quantity"]
            total_price = item_data["total_price"]

            if quantity <= 0:
                raise serializers.ValidationError(
                    "Quantity must be greater than zero."
                )

            unit_price = total_price / quantity

            PurchaseItem.objects.create(
                purchase=purchase,
                product=item_data["product"],
                quantity=quantity,
                total_price=total_price,
                unit_price=unit_price,
            )

        process_purchase(purchase)

        return purchase


# ---------------------------------

class StockUsageSerializer(serializers.ModelSerializer):

    class Meta:
        model = StockUsage

        fields = [
            "id",
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