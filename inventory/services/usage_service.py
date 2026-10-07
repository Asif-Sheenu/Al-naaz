from decimal import Decimal

from rest_framework.exceptions import ValidationError
from django.db import IntegrityError, transaction

from ..models import (
    StockUsage,
    StockBalance,
    StockLedger,
)


def _get_or_create_locked_balance(branch, product):
    """
    Get the current stock row and lock it.

    If the StockBalance row does not exist, create it safely.
    The unique constraint on (branch, product) protects against
    concurrent creation.
    """

    try:
        return (
            StockBalance.objects
            .select_for_update()
            .get(
                branch=branch,
                product=product,
            )
        )

    except StockBalance.DoesNotExist:

        try:
            with transaction.atomic():
                StockBalance.objects.create(
                    branch=branch,
                    product=product,
                    quantity=Decimal("0"),
                )

        except IntegrityError:
            # Another concurrent transaction created the row.
            pass

def _validate_movement_date(branch, product, movement_date):
    """
    Prevent inserting a stock movement earlier than the
    latest existing movement for this branch and product.
    """

    latest_movement = (
        StockLedger.objects
        .filter(
            branch=branch,
            product=product,
        )
        .order_by("-movement_date", "-id")
        .first()
    )

    if latest_movement and movement_date < latest_movement.movement_date:
        raise ValidationError(
            f"Usage date cannot be earlier than the latest "
            f"stock movement date ({latest_movement.movement_date})."
        )

def _write_ledger(
    *,
    branch,
    product,
    movement_type,
    quantity,
    balance_before,
    balance_after,
    reference_type,
    reference_id,
    movement_date,
    remarks="",
    created_by=None,
):
    """
    Create immutable stock movement history.
    """

    return StockLedger.objects.create(
        branch=branch,
        product=product,
        movement_type=movement_type,
        quantity=quantity,
        balance_before=balance_before,
        balance_after=balance_after,
        reference_type=reference_type,
        reference_id=reference_id,
        movement_date=movement_date,
        remarks=remarks,
        created_by=created_by,
    )


@transaction.atomic
def process_usage(usage):

    usage = (
        StockUsage.objects
        .select_for_update()
        .select_related(
            "branch",
            "product",
        )
        .get(pk=usage.pk)
    )

    # Prevent processing the same usage twice.
    already_processed = StockLedger.objects.filter(
        reference_type=StockLedger.ReferenceType.STOCK_USAGE,
        reference_id=usage.id,
    ).exists()

    if already_processed:
        raise ValidationError(
            f"Stock usage #{usage.id} has already been processed."
        )

    if usage.quantity <= 0:
        raise ValidationError(
            "Usage quantity must be greater than zero."
        )

    _validate_movement_date(
        branch=usage.branch,
        product=usage.product,
        movement_date=usage.usage_date,
    )

    balance = _get_or_create_locked_balance(
        branch=usage.branch,
        product=usage.product,
    )

    balance_before = balance.quantity

    if usage.quantity > balance_before:
        raise ValidationError(
            f"Insufficient stock. "
            f"Available stock: {balance_before}"
        )

    balance_after = (
        balance_before - usage.quantity
    )

    balance.quantity = balance_after

    balance.save(
        update_fields=[
            "quantity",
            "updated_at",
        ]
    )

    _write_ledger(
        branch=usage.branch,
        product=usage.product,
        movement_type=StockLedger.MovementType.USAGE,
        quantity=-usage.quantity,
        balance_before=balance_before,
        balance_after=balance_after,
        reference_type=StockLedger.ReferenceType.STOCK_USAGE,
        reference_id=usage.id,
        movement_date=usage.usage_date,
        remarks=f"Usage #{usage.id}",
        created_by=usage.created_by,
    )

    return usage