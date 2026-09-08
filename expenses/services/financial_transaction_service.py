from decimal import Decimal

from django.db import transaction

from expenses.models import FinancialTransaction


@transaction.atomic
def create_financial_transaction(
    *,
    branch,
    account,
    transaction_type,
    direction,
    amount,
    transaction_date,
    created_by,
    description="",
    reference="",
):
    # 1. Amount validation
    if amount <= Decimal("0.00"):
        raise ValueError(
            "Transaction amount must be greater than zero."
        )

    # 2. Branch validation
    if account.branch_id != branch.id:
        raise ValueError(
            "Financial account does not belong to this branch."
        )

    # 3. Account status validation
    if not account.is_active:
        raise ValueError(
            "Cannot create a transaction for an inactive account."
        )

    # 4. Transaction type / direction validation
    valid_directions = {
        FinancialTransaction.TransactionType.OPENING_BALANCE:
            FinancialTransaction.Direction.IN,

        FinancialTransaction.TransactionType.REVENUE:
            FinancialTransaction.Direction.IN,

        FinancialTransaction.TransactionType.EXPENSE:
            FinancialTransaction.Direction.OUT,

        FinancialTransaction.TransactionType.SUPPLIER_PAYMENT:
            FinancialTransaction.Direction.OUT,

        FinancialTransaction.TransactionType.ASSET_PURCHASE:
            FinancialTransaction.Direction.OUT,

        FinancialTransaction.TransactionType.TRANSFER_IN:
            FinancialTransaction.Direction.IN,

        FinancialTransaction.TransactionType.TRANSFER_OUT:
            FinancialTransaction.Direction.OUT,
    }

    expected_direction = valid_directions.get(transaction_type)

    if expected_direction is not None:
        if direction != expected_direction:
            raise ValueError(
                f"{transaction_type} must have direction "
                f"{expected_direction}."
            )

    # 5. Create transaction
    transaction_obj = FinancialTransaction.objects.create(
        branch=branch,
        account=account,
        transaction_type=transaction_type,
        direction=direction,
        amount=amount,
        transaction_date=transaction_date,
        description=description,
        reference=reference,
        created_by=created_by,
    )

    return transaction_obj