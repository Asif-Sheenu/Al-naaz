from rest_framework import serializers
from organization.models import Branch
from .models import (
    ExpenseCategory,
    Expense,
    FinancialAccount,
    FinancialTransaction,
    DailySales,
    DailySalesPayment,
    Receivable,
    ReceivableSettlement,
    DeliveryPartner,
DeliveryPartnerCommissionRate,
ExpenseAdjustment,
SupplierPayable
)


from organization.services.access_service import (
    get_accessible_branches,
)
from expenses.services.daily_sales_service import create_daily_sales
from decimal import Decimal
from expenses.models import SupplierPayment

class FinancialAccountSerializer(serializers.ModelSerializer):

    branch_name = serializers.CharField(
        source="branch.name",
        read_only=True,
    )

    created_by_name = serializers.CharField(
    source="created_by.username",
    read_only=True,
    )

    class Meta:
        model = FinancialAccount

        fields = [
            "id",
            "branch",
            "branch_name",
            "name",
            "created_by_name",
            "account_type",
            "account_purpose",
            "opening_balance",
            "opening_balance_date",
            "is_active",
            "created_by",
            "created_at",
            "updated_at",
        ]

        read_only_fields = [
            "id",
            "branch_name",
            "created_by",
            "created_at",
            "updated_at",
        ]

    def validate_branch(self, branch):

        request = self.context.get("request")

        if not request:
            return branch

        user = request.user

        if user.is_superuser or user.role == "ADMIN":
            return branch

        if not get_accessible_branches(user).filter(
            pk=branch.pk
        ).exists():

            raise serializers.ValidationError(
                "You do not have access to this branch."
            )

        return branch

    def validate_opening_balance(self, value):

        if value < 0:
            raise serializers.ValidationError(
                "Opening balance cannot be negative."
            )

        return value


    def validate(self, attrs):
        account_type = attrs.get("account_type")

        # Important for PATCH:
        # if account_type isn't being changed, use the existing account type
        if account_type is None and self.instance:
            account_type = self.instance.account_type

        account_purpose = attrs.get(
            "account_purpose",
            self.instance.account_purpose if self.instance else FinancialAccount.AccountPurpose.GENERAL,
        )

        valid_purposes = {
            FinancialAccount.AccountType.CASH: {
                FinancialAccount.AccountPurpose.GENERAL,
                FinancialAccount.AccountPurpose.CASH,
            },
            FinancialAccount.AccountType.UPI: {
                FinancialAccount.AccountPurpose.GENERAL,
                FinancialAccount.AccountPurpose.UPI,
            },
            FinancialAccount.AccountType.BANK: {
                FinancialAccount.AccountPurpose.GENERAL,
            },
            FinancialAccount.AccountType.PETTY_CASH: {
                FinancialAccount.AccountPurpose.GENERAL,
                FinancialAccount.AccountPurpose.CASH,
            },
            FinancialAccount.AccountType.RECEIVABLE: {
                FinancialAccount.AccountPurpose.CARD_RECEIVABLE,
                FinancialAccount.AccountPurpose.FOOD_DELIVERY_RECEIVABLE,
            },
        }

        allowed_purposes = valid_purposes.get(account_type, set())

        if account_purpose not in allowed_purposes:
            raise serializers.ValidationError({
                "account_purpose": (
                    f"Invalid account purpose for account type '{account_type}'."
                )
            })

        return attrs


class ExpenseCategorySerializer(serializers.ModelSerializer):

    class Meta:
        model = ExpenseCategory

        fields = [
            "id",
            "name",
            "is_active",
            "created_at",
        ]

        read_only_fields = [
            "id",
            "created_at",
        ]

class ExpenseSerializer(serializers.ModelSerializer):

    category_name = serializers.CharField(
        source="category.name",
        read_only=True
    )

    branch_name = serializers.CharField(
        source="branch.name",
        read_only=True
    )

    payment_account_name = serializers.CharField(
        source="payment_account.name",
        read_only=True
    )

    created_by_name = serializers.CharField(
        source="created_by.username",
        read_only=True
    )

    class Meta:
        model = Expense

        fields = [
            "id",
            "branch",
            "branch_name",
            "category",
            "category_name",
            "payment_account",
            "payment_account_name",
            "amount",
            "expense_date",
            "description",
            "created_by",
            "created_by_name",
            "created_at",
            "updated_at",
        ]

        read_only_fields = [
            "id",
            "branch_name",
            "category_name",
            "payment_account_name",
            "created_by",
            "created_by_name",
            "created_at",
            "updated_at",
        ]

    def validate_amount(self, value):

        if value <= 0:
            raise serializers.ValidationError(
                "Expense amount must be greater than zero."
            )

        return value

    def validate_category(self, value):

        if not value.is_active:
            raise serializers.ValidationError(
                "This expense category is inactive."
            )

        return value

    def validate_branch(self, branch):

        request = self.context.get("request")

        if not request:
            return branch

        user = request.user

        if user.is_superuser or user.role == "ADMIN":
            return branch

        if not get_accessible_branches(user).filter(
            pk=branch.pk
        ).exists():

            raise serializers.ValidationError(
                "You do not have access to this branch."
            )

        return branch

    def validate_payment_account(self, payment_account):

        if not payment_account.is_active:
            raise serializers.ValidationError(
                "This financial account is inactive."
            )

        if payment_account.account_type not in [
            FinancialAccount.AccountType.CASH,
            FinancialAccount.AccountType.BANK,
            FinancialAccount.AccountType.UPI,
            FinancialAccount.AccountType.PETTY_CASH,
        ]:
            raise serializers.ValidationError(
                "This account cannot be used to pay an expense."
            )

        return payment_account

    def validate(self, attrs):

        branch = attrs.get("branch")

        # Important for PATCH requests:
        # if branch isn't supplied, use the existing expense branch.
        if branch is None and self.instance:
            branch = self.instance.branch

        payment_account = attrs.get("payment_account")

        # Important for PATCH requests:
        # if payment_account isn't supplied, use the existing one.
        if payment_account is None and self.instance:
            payment_account = self.instance.payment_account

        if branch and payment_account:

            if payment_account.branch_id != branch.id:
                raise serializers.ValidationError({
                    "payment_account": (
                        "Payment account must belong to the selected branch."
                    )
                })

        return attrs

class AddPettyCashSerializer(serializers.Serializer):

    amount = serializers.DecimalField(
        max_digits=12,
        decimal_places=2
    )

    transaction_date = serializers.DateField()

    remarks = serializers.CharField(
        required=False,
        allow_blank=True
    )

    def validate_amount(self, value):

        if value <= 0:
            raise serializers.ValidationError(
                "Amount must be greater than zero."
            )

        return value        

    # reposrt service =--------------------------------------------------------------------------------- 


class ExpenseReportSerializer(serializers.Serializer):

    start_date = serializers.DateField()

    end_date = serializers.DateField()

    opening_balance = serializers.DecimalField(
        max_digits=12,
        decimal_places=2
    )

    total_cash_added = serializers.DecimalField(
        max_digits=12,
        decimal_places=2
    )

    total_expense = serializers.DecimalField(
        max_digits=12,
        decimal_places=2
    )

    expense_count = serializers.IntegerField()

    closing_balance = serializers.DecimalField(
        max_digits=12,
        decimal_places=2
    )

    category_totals = serializers.ListField()




class TransferSerializer(serializers.Serializer):

    from_account = serializers.PrimaryKeyRelatedField(
        queryset=FinancialAccount.objects.filter(is_active=True)
    )

    to_account = serializers.PrimaryKeyRelatedField(
        queryset=FinancialAccount.objects.filter(is_active=True)
    )

    amount = serializers.DecimalField(
        max_digits=14,
        decimal_places=2
    )

    transaction_date = serializers.DateField()

    description = serializers.CharField(
        required=False,
        allow_blank=True
    )

    reference = serializers.CharField(
        required=False,
        allow_blank=True,
        max_length=100
    )

    idempotency_key = serializers.UUIDField(
        required=False,
        allow_null=True
    )

    def validate_amount(self, value):

        if value <= 0:
            raise serializers.ValidationError(
                "Transfer amount must be greater than zero."
            )

        return value

    def validate(self, attrs):

        from_account = attrs["from_account"]
        to_account = attrs["to_account"]

        if from_account.pk == to_account.pk:
            raise serializers.ValidationError(
                "Source and destination accounts must be different."
            )

        if from_account.branch_id != to_account.branch_id:
            raise serializers.ValidationError(
                "Transfers are only allowed between accounts "
                "of the same branch."
            )

        return attrs    





class FinancialTransactionSerializer(serializers.ModelSerializer):

    account_name = serializers.CharField(
        source="account.name",
        read_only=True,
    )

    branch_name = serializers.CharField(
        source="branch.name",
        read_only=True,
    )

    created_by_name = serializers.CharField(
        source="created_by.username",
        read_only=True,
    )

    class Meta:
        model = FinancialTransaction

        fields = [
            "id",
            "branch",
            "branch_name",
            "account",
            "account_name",
            "transaction_type",
            "direction",
            "amount",
            "transaction_date",
            "description",
            "reference",
            "transfer_group_id",
            "created_by",
            "created_by_name",
            "created_at",
        ]

        read_only_fields = fields    


class DailySalesPaymentSerializer(serializers.ModelSerializer):

    class Meta:
        model = DailySalesPayment

        fields = [
            "id",
            "payment_method",
            "amount",
            "delivery_partner",
            "platform",
            "created_at",
        ]

        read_only_fields = [
            "id",
            "created_at",
            "platform",
        ]

    def validate_amount(self, value):

        if value <= 0:
            raise serializers.ValidationError(
                "Payment amount must be greater than zero."
            )

        return value

    def validate(self, attrs):

        payment_method = attrs.get("payment_method")
        delivery_partner = attrs.get("delivery_partner")

        # --------------------------------------------------
        # FOOD DELIVERY
        # --------------------------------------------------

        if (
            payment_method
            == DailySalesPayment.PaymentMethod.FOOD_DELIVERY
        ):

            if not delivery_partner:
                raise serializers.ValidationError({
                    "delivery_partner": (
                        "Delivery partner is required "
                        "for food delivery payments."
                    )
                })

            if not delivery_partner.is_active:
                raise serializers.ValidationError({
                    "delivery_partner": (
                        "This delivery partner is inactive."
                    )
                })

            # Make sure the partner belongs to the same
            # branch as the DailySales record.
            daily_sales = self.context.get(
                "daily_sales"
            )

            if daily_sales:
                if delivery_partner.branch_id != daily_sales.branch_id:
                    raise serializers.ValidationError({
                        "delivery_partner": (
                            "Delivery partner must belong "
                            "to the same branch as the daily sales."
                        )
                    })

        # --------------------------------------------------
        # NON FOOD DELIVERY
        # --------------------------------------------------

        else:

            if delivery_partner:
                raise serializers.ValidationError({
                    "delivery_partner": (
                        "Delivery partner should only be "
                        "provided for food delivery payments."
                    )
                })

        return attrs

class DailySalesSerializer(serializers.ModelSerializer):

    payments = DailySalesPaymentSerializer(
        many=True
    )

    branch_name = serializers.CharField(
        source="branch.name",
        read_only=True,
    )

    created_by_name = serializers.CharField(
        source="created_by.username",
        read_only=True,
    )

    class Meta:
        model = DailySales

        fields = [
            "id",
            "branch",
            "branch_name",
            "business_date",
            "total_gross",
            "status",
            "payments",
            "created_by",
            "created_by_name",
            "created_at",
            "updated_at",
        ]

        read_only_fields = [
            "id",
            "branch_name",
            "total_gross",
            "created_by",
            "created_by_name",
            "created_at",
            "updated_at",
        ]

    def validate_branch(self, branch):

        request = self.context.get("request")

        if not request:
            return branch

        user = request.user

        if user.is_superuser or user.role == "ADMIN":
            return branch

        if not get_accessible_branches(user).filter(
            pk=branch.pk
        ).exists():

            raise serializers.ValidationError(
                "You do not have access to this branch."
            )

        return branch

    def validate_business_date(self, value):

        from django.utils import timezone

        today = timezone.localdate()

        if value > today:
            raise serializers.ValidationError(
                "Business date cannot be in the future."
            )

        return value

    def validate(self, attrs):

        if (
            self.instance
            and self.instance.status == DailySales.Status.POSTED
        ):
            raise serializers.ValidationError(
                "Posted daily sales cannot be modified."
            )

        payments = attrs.get("payments")

        # --------------------------------------------------
        # Payments were supplied
        # --------------------------------------------------

        if payments is not None:

            if not payments:
                raise serializers.ValidationError({
                    "payments": (
                        "At least one payment entry is required."
                    )
                })

            total = sum(
                payment["amount"]
                for payment in payments
            )

            if total <= 0:
                raise serializers.ValidationError({
                    "payments": (
                        "Total sales amount must be greater than zero."
                    )
                })

            # --------------------------------------------------
            # Branch validation for delivery partner
            # --------------------------------------------------

            branch = attrs.get(
                "branch",
                self.instance.branch if self.instance else None
            )

            for payment in payments:

                if (
                    payment["payment_method"]
                    == DailySalesPayment.PaymentMethod.FOOD_DELIVERY
                ):

                    delivery_partner = payment.get(
                        "delivery_partner"
                    )

                    if (
                        delivery_partner
                        and delivery_partner.branch_id != branch.id
                    ):
                        raise serializers.ValidationError({
                            "payments": (
                                f"Delivery partner "
                                f"'{delivery_partner.name}' "
                                "must belong to the same branch "
                                "as the daily sales."
                            )
                        })

        return attrs


    def create(self, validated_data):

        payments = validated_data.pop("payments")

        daily_sales = create_daily_sales(
                branch=validated_data["branch"],
                business_date=validated_data["business_date"],
                payments=payments,
                created_by=self.context["request"].user,
            )

        return daily_sales


    def update(self, instance, validated_data):

        payments = validated_data.pop("payments", None)

        # --------------------------------------------------
        # Posted sales cannot be modified
        # --------------------------------------------------

        if instance.status == DailySales.Status.POSTED:
            raise serializers.ValidationError(
                "Posted daily sales cannot be modified."
            )

        # --------------------------------------------------
        # Update Daily Sales fields
        # --------------------------------------------------

        if "branch" in validated_data:
            instance.branch = validated_data["branch"]

        if "business_date" in validated_data:
            instance.business_date = validated_data["business_date"]

        # --------------------------------------------------
        # Update payments
        # --------------------------------------------------

        if payments is not None:

            # Delete existing draft payments
            instance.payments.all().delete()

            # Create the new payment entries
            for payment_data in payments:
                DailySalesPayment.objects.create(
                    daily_sales=instance,
                    **payment_data
                )

            # Recalculate total
            instance.total_gross = sum(
                payment["amount"]
                for payment in payments
            )

        instance.save()

        return instance

class ReceivableSettlementSerializer(serializers.Serializer):

    receivable = serializers.PrimaryKeyRelatedField(
        queryset=Receivable.objects.all()
    )

    destination_account = serializers.PrimaryKeyRelatedField(
        queryset=FinancialAccount.objects.all()
    )

    gross_amount = serializers.DecimalField(
        max_digits=14,
        decimal_places=2,
    )

    settlement_date = serializers.DateField()

    reference = serializers.CharField(
        max_length=100,
        required=False,
        allow_blank=True,
    )

    description = serializers.CharField(
        max_length=255,
        required=False,
        allow_blank=True,
    )

    def validate_gross_amount(self, value):
        if value <= Decimal("0.00"):
            raise serializers.ValidationError(
                "Gross settlement amount must be greater than zero."
            )
        return value
    
class ReceivableSerializer(serializers.ModelSerializer):

    branch_name = serializers.CharField(
        source="branch.name",
        read_only=True,
    )

    payment_method = serializers.CharField(
        source="daily_sales_payment.payment_method",
        read_only=True,
    )

    platform = serializers.CharField(
        source="daily_sales_payment.platform",
        read_only=True,
    )

    business_date = serializers.DateField(
        source="daily_sales_payment.daily_sales.business_date",
        read_only=True,
    )

    delivery_partner_name = serializers.CharField(
        source="delivery_partner.name",
        read_only=True,
        )

    class Meta:
        model = Receivable

        fields = [
            "id",
            "branch",
            "branch_name",
            "daily_sales_payment",
            "payment_method",
            "platform",
            "receivable_account",
            "delivery_partner",
            "delivery_partner_name",
            "gross_amount",
            "commission_rate",
            "commission_amount",
            "expected_net_amount",
            "settled_amount",
            "outstanding_amount",
            "status",
            "business_date",
            "created_by",
            "created_at",
            "updated_at",
        ]

        read_only_fields = [
            "id",
            "branch",
            "branch_name",
            "daily_sales_payment",
            "payment_method",
            "platform",
            "receivable_account",
            "delivery_partner",
            "delivery_partner_name",
            "gross_amount",
            "commission_rate",
            "commission_amount",
            "expected_net_amount",
            "settled_amount",
            "outstanding_amount",
            "status",
            "business_date",
            "created_by",
            "created_at",
            "updated_at",
        ]


class DeliveryPartnerSerializer(serializers.ModelSerializer):

    class Meta:
        model = DeliveryPartner
        fields = [
            "id",
            "branch",
            "name",
            "is_active",
            "created_by",
            "created_at",
            "updated_at",
        ]

        read_only_fields = [
            "id",
            "created_by",
            "created_at",
            "updated_at",
        ]

class DeliveryPartnerCommissionRateSerializer(serializers.ModelSerializer):

    class Meta:
        model = DeliveryPartnerCommissionRate
        fields = [
            "id",
            "delivery_partner",
            "commission_rate",
            "effective_from",
            "effective_to",
            "created_by",
            "created_at",
        ]

        read_only_fields = [
            "id",
            "created_by",
            "created_at",
        ]

    def validate_commission_rate(self, value):

        if value < Decimal("0.00") or value > Decimal("100.00"):
            raise serializers.ValidationError(
                "Commission rate must be between 0% and 100%."
            )

        return value

    def validate(self, attrs):

        delivery_partner = attrs.get("delivery_partner")
        effective_from = attrs.get("effective_from")
        effective_to = attrs.get("effective_to")

        if effective_to and effective_to < effective_from:
            raise serializers.ValidationError(
                {
                    "effective_to": (
                        "Effective-to date cannot be earlier "
                        "than effective-from date."
                    )
                }
            )

        # Check for overlapping commission periods
        existing_rates = DeliveryPartnerCommissionRate.objects.filter(
            delivery_partner=delivery_partner
        )

        if self.instance:
            existing_rates = existing_rates.exclude(
                pk=self.instance.pk
            )

        for rate in existing_rates:

            existing_from = rate.effective_from
            existing_to = rate.effective_to

            # New rate starts after existing rate ends
            if existing_to and effective_from > existing_to:
                continue

            # Existing rate starts after new rate ends
            if effective_to and existing_from > effective_to:
                continue

            raise serializers.ValidationError(
                {
                    "effective_from": (
                        "This commission period overlaps "
                        "with an existing commission rate."
                    )
                }
            )

        return attrs


class ChangeCommissionRateSerializer(serializers.Serializer):

    commission_rate = serializers.DecimalField(
        max_digits=5,
        decimal_places=2,
    )

    effective_from = serializers.DateField()

    def validate_commission_rate(self, value):

        if value < Decimal("0.00"):
            raise serializers.ValidationError(
                "Commission rate cannot be negative."
            )

        if value > Decimal("100.00"):
            raise serializers.ValidationError(
                "Commission rate cannot exceed 100%."
            )

        return value    



class ExpenseAdjustmentSerializer(serializers.ModelSerializer):

    rejected_by = serializers.PrimaryKeyRelatedField(
    read_only=True
    )

    rejected_by_name = serializers.CharField(
        source="rejected_by.username",
        read_only=True
    )

    expense_id = serializers.IntegerField(
        source="expense.id",
        read_only=True,
    )

    requested_by_name = serializers.CharField(
        source="requested_by.username",
        read_only=True,
    )

    approved_by_name = serializers.CharField(
        source="approved_by.username",
        read_only=True,
    )

    old_payment_account_name = serializers.CharField(
        source="old_payment_account.name",
        read_only=True,
    )

    new_payment_account_name = serializers.CharField(
        source="new_payment_account.name",
        read_only=True,
    )

    old_category_name = serializers.CharField(
        source="old_category.name",
        read_only=True,
    )

    new_category_name = serializers.CharField(
        source="new_category.name",
        read_only=True,
    )

    class Meta:
        model = ExpenseAdjustment

        fields = [
            "id",

            "expense",
            "expense_id",

            "rejected_by",
            "rejected_by_name",

            "status",

            "old_amount",
            "new_amount",

            "old_payment_account",
            "old_payment_account_name",

            "new_payment_account",
            "new_payment_account_name",

            "old_expense_date",
            "new_expense_date",

            "old_category",
            "old_category_name",

            "new_category",
            "new_category_name",

            "old_description",
            "new_description",

            "reason",
            "rejection_reason",

            "requested_by",
            "requested_by_name",

            "approved_by",
            "approved_by_name",

            "requested_at",
            "approved_at",
            "rejected_at",
        ]

        read_only_fields = [
            "id",
            "status",

            "old_amount",
            "old_payment_account",
            "old_payment_account_name",
            "old_expense_date",
            "old_category",
            "old_category_name",
            "old_description",

            "expense_id",

            "requested_by",
            "requested_by_name",

            "approved_by",
            "approved_by_name",

            "requested_at",
            "approved_at",
            "rejected_at",

            "rejection_reason",
        ]    



class ExpenseAdjustmentRejectSerializer(serializers.Serializer):

    rejection_reason = serializers.CharField(
        required=True,
        allow_blank=False,
        trim_whitespace=True,
    )        



class SupplierPaymentSerializer(serializers.ModelSerializer):

    supplier_name = serializers.CharField(
        source="payable.supplier.name",
        read_only=True
    )

    payable_status = serializers.CharField(
        source="payable.status",
        read_only=True
    )

    class Meta:
        model = SupplierPayment

        fields = [
            "id",
            "payable",
            "supplier_name",
            "payment_account",
            "amount",
            "payment_date",
            "reference",
            "remarks",
            "created_by",
            "payable_status",
            "created_at",
        ]

        read_only_fields = [
            "id",
            "supplier_name",
            "created_by",
            "payable_status",
            "created_at",
        ]    


class SupplierPaymentSerializer(serializers.ModelSerializer):

    supplier_name = serializers.CharField(
        source="payable.supplier.name",
        read_only=True,
    )

    payable_status = serializers.CharField(
        source="payable.status",
        read_only=True,
    )

    class Meta:
        model = SupplierPayment

        fields = [
            "id",
            "payable",
            "supplier_name",
            "payment_account",
            "amount",
            "payment_date",
            "reference",
            "remarks",
            "created_by",
            "payable_status",
            "created_at",
        ]

        read_only_fields = [
            "id",
            "supplier_name",
            "payable_status",
            "created_by",
            "created_at",
        ]

    def validate_amount(self, value):

        if value <= Decimal("0.00"):
            raise serializers.ValidationError(
                "Payment amount must be greater than zero."
            )

        return value

    def validate_payment_account(self, account):

        if not account.is_active:
            raise serializers.ValidationError(
                "Cannot make payment using an inactive account."
            )

        return account


class SupplierPaymentHistorySerializer(
    serializers.ModelSerializer
):

    payment_account_name = serializers.CharField(
        source="payment_account.name",
        read_only=True,
    )

    created_by_name = serializers.CharField(
        source="created_by.username",
        read_only=True,
    )

    class Meta:
        model = SupplierPayment

        fields = [
            "id",
            "amount",
            "payment_date",
            "payment_account",
            "payment_account_name",
            "reference",
            "remarks",
            "created_by",
            "created_by_name",
            "created_at",
        ]

        read_only_fields = fields


class SupplierPayableSerializer(
    serializers.ModelSerializer
):

    supplier_name = serializers.CharField(
        source="supplier.name",
        read_only=True,
    )

    branch_name = serializers.CharField(
        source="branch.name",
        read_only=True,
    )

    purchase_invoice_number = serializers.CharField(
        source="purchase.invoice_number",
        read_only=True,
    )

    purchase_date = serializers.DateField(
        source="purchase.purchase_date",
        read_only=True,
    )

    payments = SupplierPaymentHistorySerializer(
        many=True,
        read_only=True,
    )

    class Meta:
        model = SupplierPayable

        fields = [
            "id",

            "purchase",
            "purchase_invoice_number",
            "purchase_date",

            "supplier",
            "supplier_name",

            "branch",
            "branch_name",

            "total_amount",
            "paid_amount",
            "outstanding_amount",
            "status",

            "payments",

            "created_at",
            "updated_at",
        ]

        read_only_fields = fields        