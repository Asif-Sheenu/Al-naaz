from decimal import Decimal
from uuid import uuid4

from django.db import transaction

from expenses.models import (
    FinancialAccount,
    FinancialTransaction,
    Receivable,
    ReceivableSettlement,
)


@transaction.atomic
def settle_receivable(
    *,
    receivable,
    destination_account,
    gross_amount,
    settlement_date,
    created_by,
    reference="",
    description="",
):
    gross_amount = Decimal(gross_amount)

    if gross_amount <= Decimal("0.00"):
        raise ValueError(
            "Gross settlement amount must be greater than zero."
        )

    # --------------------------------------------------
    # 1. Lock the receivable
    # --------------------------------------------------

    receivable = (
        Receivable.objects
        .select_for_update()
        .select_related(
            "branch",
            "receivable_account",
        )
        .get(pk=receivable.pk)
    )

    if receivable.status == Receivable.Status.SETTLED:
        raise ValueError(
            "This receivable has already been fully settled."
        )

    # --------------------------------------------------
    # 2. Validate settlement amount
    # --------------------------------------------------

    if gross_amount > receivable.outstanding_amount:
        raise ValueError(
            f"Settlement amount cannot exceed outstanding "
            f"receivable of ₹{receivable.outstanding_amount}."
        )

    # --------------------------------------------------
    # 3. Validate destination account
    # --------------------------------------------------

    if receivable.branch_id != destination_account.branch_id:
        raise ValueError(
            "Receivable and destination account must belong "
            "to the same branch."
        )

    if destination_account.account_type not in {
        FinancialAccount.AccountType.CASH,
        FinancialAccount.AccountType.BANK,
        FinancialAccount.AccountType.UPI,
    }:
        raise ValueError(
            "Destination account must be a cash, bank, or UPI account."
        )

    # --------------------------------------------------
    # 4. Calculate commission proportionally
    # --------------------------------------------------

    if receivable.gross_amount <= Decimal("0.00"):
        raise ValueError(
            "Receivable gross amount must be greater than zero."
        )

    commission_amount = (
        gross_amount
        * receivable.commission_rate
        / Decimal("100.00")
    ).quantize(Decimal("0.01"))

    received_amount = (
        gross_amount - commission_amount
    ).quantize(Decimal("0.01"))

    if received_amount <= Decimal("0.00"):
        raise ValueError(
            "Received amount must be greater than zero."
        )

    # --------------------------------------------------
    # 5. Lock financial accounts
    # --------------------------------------------------

    receivable_account = (
        FinancialAccount.objects
        .select_for_update()
        .get(pk=receivable.receivable_account_id)
    )

    destination_account = (
        FinancialAccount.objects
        .select_for_update()
        .get(pk=destination_account.pk)
    )

    # --------------------------------------------------
    # 6. Create settlement group
    # --------------------------------------------------

    settlement_group_id = uuid4()

    # --------------------------------------------------
    # 7. Reduce receivable
    # --------------------------------------------------

    FinancialTransaction.objects.create(
        branch=receivable.branch,
        account=receivable_account,
        transaction_type=(
            FinancialTransaction.TransactionType.TRANSFER_OUT
        ),
        direction=FinancialTransaction.Direction.OUT,
        amount=gross_amount,
        transaction_date=settlement_date,
        description=(
            description or "Receivable settlement"
        ),
        reference=(
            reference
            or f"SETTLEMENT-{settlement_group_id}"
        ),
        transfer_group_id=settlement_group_id,
        created_by=created_by,
    )

    # --------------------------------------------------
    # 8. Increase actual cash/bank/UPI
    # --------------------------------------------------

    FinancialTransaction.objects.create(
        branch=receivable.branch,
        account=destination_account,
        transaction_type=(
            FinancialTransaction.TransactionType.TRANSFER_IN
        ),
        direction=FinancialTransaction.Direction.IN,
        amount=received_amount,
        transaction_date=settlement_date,
        description=(
            description or "Receivable settlement"
        ),
        reference=(
            reference
            or f"SETTLEMENT-{settlement_group_id}"
        ),
        transfer_group_id=settlement_group_id,
        created_by=created_by,
    )

    # --------------------------------------------------
    # 9. Save settlement history
    # --------------------------------------------------

    settlement = ReceivableSettlement.objects.create(
        receivable=receivable,
        destination_account=destination_account,
        gross_amount=gross_amount,
        commission_amount=commission_amount,
        received_amount=received_amount,
        settlement_date=settlement_date,
        reference=reference,
        description=description,
        created_by=created_by,
    )

    # --------------------------------------------------
    # 10. Update receivable
    # --------------------------------------------------

    receivable.settled_amount += gross_amount

    receivable.outstanding_amount = (
        receivable.gross_amount
        - receivable.settled_amount
    )

    if receivable.outstanding_amount == Decimal("0.00"):
        receivable.status = Receivable.Status.SETTLED
    else:
        receivable.status = (
            Receivable.Status.PARTIALLY_SETTLED
        )

    receivable.save(
        update_fields=[
            "settled_amount",
            "outstanding_amount",
            "status",
            "updated_at",
        ]
    )

    return settlement