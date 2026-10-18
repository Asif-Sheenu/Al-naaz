import logging
import uuid

from decimal import Decimal, ROUND_HALF_UP
from datetime import date

from django.db import transaction

from expenses.models import FinancialAccount, FinancialTransaction
from expenses.services.financial_account_service import get_account_balance

from notifications.services.notification_service import (
    notify_admins_and_managers,
)

logger = logging.getLogger(__name__)


def _notify_transfer_recorded(
    *,
    branch,
    transfer_out_id,
    transfer_in_id,
    source_account_name,
    destination_account_name,
    amount,
    transaction_date,
):
    """
    Notify admins and branch managers after a transfer commits.
    """
    try:
        notify_admins_and_managers(
            notification_type="INFO",
            title="Money Transfer Recorded",
            message=(
                f"Transfer of ₹{amount} recorded from "
                f"'{source_account_name}' to "
                f"'{destination_account_name}' on "
                f"{transaction_date}. "
                f"Transfer Out ID: {transfer_out_id}. "
                f"Transfer In ID: {transfer_in_id}."
            ),
            module="FINANCE",
            object_id=transfer_out_id,
            branch=branch,
        )
    except Exception:
        logger.exception(
            "Failed to send notification for transfer ID %s",
            transfer_out_id,
        )


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

    # 1. Validate amount

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

    # 2. Check idempotency
    # Existing transfers return without creating a new notification.

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
                    transfer_group_id=(
                        existing_transfer.transfer_group_id
                    ),
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

    # 3. Validate accounts are different

    if from_account.id == to_account.id:
        raise ValueError(
            "Source and destination accounts must be different."
        )

    # 4. Validate account status

    if not from_account.is_active:
        raise ValueError(
            "Source account is inactive."
        )

    if not to_account.is_active:
        raise ValueError(
            "Destination account is inactive."
        )

    # 5. Validate branch

    if from_account.branch_id != to_account.branch_id:
        raise ValueError(
            "Transfers are only allowed between accounts "
            "of the same branch."
        )

    # 6. Lock both account rows in ID order

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

    # 7. Re-check account status after locking

    if not source_account.is_active:
        raise ValueError(
            "Source account is inactive."
        )

    if not destination_account.is_active:
        raise ValueError(
            "Destination account is inactive."
        )

    # 8. Check source balance

    source_balance = get_account_balance(source_account)

    if source_balance < amount:
        raise ValueError(
            "Insufficient balance in source account."
        )

    # 9. Generate a shared transfer group ID

    transfer_group_id = uuid.uuid4()

    # 10. Create TRANSFER_OUT

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

    # 11. Create TRANSFER_IN

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

    # 12. Notify only after the transaction commits successfully.
    # Both linked financial transactions must commit first.

    transaction.on_commit(
        lambda: _notify_transfer_recorded(
            branch=source_account.branch,
            transfer_out_id=transfer_out.id,
            transfer_in_id=transfer_in.id,
            source_account_name=source_account.name,
            destination_account_name=destination_account.name,
            amount=transfer_out.amount,
            transaction_date=transfer_out.transaction_date,
        )
    )

    return transfer_out, transfer_in