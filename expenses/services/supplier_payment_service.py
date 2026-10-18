import logging
from decimal import Decimal

from django.db import transaction

from inventory.models import Purchase

from expenses.models import (
    FinancialTransaction,
    FinancialAccount,
    SupplierPayable,
    SupplierPayment,
)

from expenses.services.financial_transaction_service import (
    create_financial_transaction,
)

from notifications.services.notification_service import (
    notify_admins_and_managers,
)

logger = logging.getLogger(__name__)


def _notify_supplier_payment(
    *,
    branch,
    payment_id,
    supplier_name,
    amount,
    outstanding_amount,
    status,
):
    """
    Notify admins and branch managers after a supplier
    payment has successfully committed.
    """
    try:
        notify_admins_and_managers(
            notification_type="INFO",
            title="Supplier Payment Recorded",
            message=(
                f"Payment of ₹{amount} recorded for supplier "
                f"{supplier_name}. Payment ID: {payment_id}. "
                f"Outstanding payable: ₹{outstanding_amount}. "
                f"Payable status: {status}."
            ),
            module="FINANCE",
            object_id=payment_id,
            branch=branch,
        )
    except Exception:
        logger.exception(
            "Failed to send notification for supplier payment ID %s",
            payment_id,
        )


@transaction.atomic
def create_supplier_payable(
    *,
    purchase,
    total_amount,
):
    if total_amount <= Decimal("0.00"):
        raise ValueError(
            "Purchase total must be greater than zero."
        )

    payable = SupplierPayable.objects.create(
        purchase=purchase,
        supplier=purchase.supplier,
        branch=purchase.branch,
        total_amount=total_amount,
        paid_amount=Decimal("0.00"),
        outstanding_amount=total_amount,
        status=SupplierPayable.Status.OPEN,
    )

    return payable


@transaction.atomic
def create_supplier_payment(
    *,
    payable,
    amount,
    payment_account,
    payment_date,
    created_by,
    reference="",
    remarks="",
):
    if amount <= Decimal("0.00"):
        raise ValueError(
            "Supplier payment must be greater than zero."
        )

    # 1. Lock the payable to prevent concurrent overpayments
    payable = (
        SupplierPayable.objects
        .select_for_update()
        .select_related(
            "supplier",
            "purchase",
            "branch",
        )
        .get(pk=payable.pk)
    )

    if amount > payable.outstanding_amount:
        raise ValueError(
            "Payment cannot be greater than the "
            "outstanding payable."
        )

    # 2. Lock and validate the payment account
    payment_account = (
        FinancialAccount.objects
        .select_for_update()
        .get(pk=payment_account.pk)
    )

    if payment_account.branch_id != payable.branch_id:
        raise ValueError(
            "Payment account does not belong to "
            "the payable's branch."
        )

    if not payment_account.is_active:
        raise ValueError(
            "Cannot make payment using an inactive account."
        )

    if payment_account.account_type not in [
        FinancialAccount.AccountType.CASH,
        FinancialAccount.AccountType.BANK,
        FinancialAccount.AccountType.UPI,
        FinancialAccount.AccountType.PETTY_CASH,
    ]:
        raise ValueError(
            "This account cannot be used to pay a supplier."
        )

    # 3. Create the supplier payment
    payment = SupplierPayment.objects.create(
        payable=payable,
        payment_account=payment_account,
        amount=amount,
        payment_date=payment_date,
        reference=reference,
        remarks=remarks,
        created_by=created_by,
    )

    # 4. Record the outgoing financial transaction
    create_financial_transaction(
        branch=payable.branch,
        account=payment_account,
        transaction_type=(
            FinancialTransaction.TransactionType.SUPPLIER_PAYMENT
        ),
        direction=FinancialTransaction.Direction.OUT,
        amount=amount,
        transaction_date=payment_date,
        created_by=created_by,
        description=(
            f"Supplier payment - {payable.supplier.name}"
        ),
        reference=(
            reference
            or f"SUPPLIER-PAYMENT-{payment.id}"
        ),
    )

    # 5. Update payable balances
    payable.paid_amount += amount
    payable.outstanding_amount -= amount

    if payable.outstanding_amount == Decimal("0.00"):
        payable.status = SupplierPayable.Status.PAID
    else:
        payable.status = SupplierPayable.Status.PARTIAL

    payable.save(
        update_fields=[
            "paid_amount",
            "outstanding_amount",
            "status",
            "updated_at",
        ]
    )

    # 6. Synchronize purchase payment status
    purchase = (
        Purchase.objects
        .select_for_update()
        .get(pk=payable.purchase_id)
    )

    if payable.outstanding_amount == Decimal("0.00"):
        purchase.payment_status = Purchase.PaymentStatus.PAID
    elif payable.paid_amount > Decimal("0.00"):
        purchase.payment_status = Purchase.PaymentStatus.PARTIAL
    else:
        purchase.payment_status = Purchase.PaymentStatus.CREDIT

    purchase.save(
        update_fields=["payment_status"]
    )

    # 7. Notify after the outermost transaction commits.
    # Capture values now so the callback uses the correct
    # payment details even if these objects change later.
    transaction.on_commit(
        lambda: _notify_supplier_payment(
            branch=payable.branch,
            payment_id=payment.id,
            supplier_name=payable.supplier.name,
            amount=payment.amount,
            outstanding_amount=payable.outstanding_amount,
            status=payable.status,
        )
    )

    return payment


@transaction.atomic
def process_supplier_purchase(
    *,
    purchase,
    total_amount,
    initial_payment,
    created_by,
):
    payable = create_supplier_payable(
        purchase=purchase,
        total_amount=total_amount,
    )

    if initial_payment:
        payment_amount = initial_payment["amount"]

        if payment_amount > Decimal("0.00"):
            create_supplier_payment(
                payable=payable,
                amount=payment_amount,
                payment_account=(
                    initial_payment["payment_account"]
                ),
                payment_date=purchase.purchase_date,
                created_by=created_by,
                reference=(
                    f"PURCHASE-{purchase.id}-INITIAL"
                ),
                remarks=(
                    f"Initial payment for "
                    f"Purchase #{purchase.id}"
                ),
            )

    # Return the latest payable values, including
    # any initial payment made above.
    payable.refresh_from_db()

    return payable