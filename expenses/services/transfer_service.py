import uuid
from decimal import Decimal, ROUND_HALF_UP
from datetime import date

from django.db import transaction

from expenses.models import FinancialAccount, FinancialTransaction
from expenses.services.financial_account_service import get_account_balance


@transaction.atomic
def transfer_money(
    *,
    from_account: FinancialAccount,
    to_account: FinancialAccount,
    amount: Decimal,
    transaction_date: date,
    created_by,
    idempotency_key=None,
    description: str = "",
    reference: str = "",
):
    """
    Transfer money from one financial account to another.

    Creates two linked transactions:

        Source account      -> TRANSFER_OUT
        Destination account -> TRANSFER_IN

    Both transactions are created atomically.
    """

    # ---------------------------------------------------------
    # 1. Validate amount
    # ---------------------------------------------------------

    if amount <= Decimal("0.00"):
        raise ValueError(
            "Transfer amount must be greater than zero."
        )

    quantized_amount = amount.quantize(
        Decimal("0.01"),
        rounding=ROUND_HALF_UP,
    )

    if quantized_amount != amount:
        raise ValueError(
            "Transfer amount cannot have more than 2 decimal places."
        )


    # ---------------------------------------------------------
# 2. Check idempotency
# ---------------------------------------------------------

    if idempotency_key is not None:

        existing_transfer = (
            FinancialTransaction.objects
            .filter(
                idempotency_key=idempotency_key,
                transaction_type=(
                    FinancialTransaction.TransactionType.TRANSFER_OUT
                ),
            )
            .first()
        )

        if existing_transfer:

            transfer_in = (
                FinancialTransaction.objects
                .filter(
                    transfer_group_id=existing_transfer.transfer_group_id,
                    transaction_type=(
                        FinancialTransaction.TransactionType.TRANSFER_IN
                    ),
                )
                .first()
            )

            if transfer_in is None:
                raise ValueError(
                    "Existing transfer is incomplete."
                )

            return existing_transfer, transfer_in                               


    # ---------------------------------------------------------
    # 3. Validate accounts are different
    # ---------------------------------------------------------

    if from_account.id == to_account.id:
        raise ValueError(
            "Source and destination accounts must be different."
        )

    # ---------------------------------------------------------
    # 4. Validate account status
    # ---------------------------------------------------------

    if not from_account.is_active:
        raise ValueError(
            "Source account is inactive."
        )

    if not to_account.is_active:
        raise ValueError(
            "Destination account is inactive."
        )

    # ---------------------------------------------------------
    # 5. Validate branch
    # ---------------------------------------------------------

    if from_account.branch_id != to_account.branch_id:
        raise ValueError(
            "Transfers are only allowed between accounts "
            "of the same branch."
        )

    # ---------------------------------------------------------
    # 6. Lock both account rows
    #
    # Always lock in ID order.
    # This prevents opposite transfers from deadlocking.
    # ---------------------------------------------------------

    account_ids = sorted([
        from_account.id,
        to_account.id,
    ])

    locked_accounts = (
        FinancialAccount.objects
        .select_for_update()
        .select_related("branch")
        .filter(id__in=account_ids)
    )

    locked_accounts = {
        account.id: account
        for account in locked_accounts
    }

    if len(locked_accounts) != 2:
        raise ValueError(
            "One or more financial accounts do not exist."
        )

    source_account = locked_accounts[from_account.id]
    destination_account = locked_accounts[to_account.id]

    # ---------------------------------------------------------
    # 7. Re-check account status after locking
    #
    # Important because the originally supplied objects may
    # have become stale before the transaction acquired locks.
    # ---------------------------------------------------------

    if not source_account.is_active:
        raise ValueError(
            "Source account is inactive."
        )

    if not destination_account.is_active:
        raise ValueError(
            "Destination account is inactive."
        )

    # ---------------------------------------------------------
    # 8. Check source balance
    # ---------------------------------------------------------

    source_balance = get_account_balance(source_account)

    if source_balance < amount:
        raise ValueError(
            "Insufficient balance in source account."
        )

    # ---------------------------------------------------------
    # 9. Generate one ID for this transfer
    #
    # Both transaction rows will share this ID.
    # ---------------------------------------------------------

    transfer_group_id = uuid.uuid4()

    # ---------------------------------------------------------
    # 10. Create TRANSFER_OUT
    # ---------------------------------------------------------

    transfer_out = FinancialTransaction.objects.create(
        branch=source_account.branch,
        account=source_account,
        transaction_type=(
            FinancialTransaction.TransactionType.TRANSFER_OUT
        ),
        direction=FinancialTransaction.Direction.OUT,
        amount=amount,
        transaction_date=transaction_date,
        description=description,
        reference=reference,
        created_by=created_by,
        transfer_group_id=transfer_group_id,
        idempotency_key=idempotency_key,
    )

    # ---------------------------------------------------------
    # 11. Create TRANSFER_IN
    # ---------------------------------------------------------

    transfer_in = FinancialTransaction.objects.create(
        branch=destination_account.branch,
        account=destination_account,
        transaction_type=(
            FinancialTransaction.TransactionType.TRANSFER_IN
        ),
        direction=FinancialTransaction.Direction.IN,
        amount=amount,
        transaction_date=transaction_date,
        description=description,
        reference=reference,
        created_by=created_by,
        transfer_group_id=transfer_group_id,
    )

    return transfer_out, transfer_in