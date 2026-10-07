from decimal import Decimal

from django.db import IntegrityError, transaction
from rest_framework.exceptions import ValidationError

from ..models import (
    StockAdjustment,
    StockBalance,
    StockLedger,
)


def _get_or_create_locked_balance(branch, product):
    """
    Get the current StockBalance row and lock it.

    If the row does not exist, create it safely.
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
            # Another concurrent transaction created it.
            pass

        return (
            StockBalance.objects
            .select_for_update()
            .get(
                branch=branch,
                product=product,
            )
        )


def _validate_movement_date(
    branch,
    product,
    movement_date,
):
    """
    Prevent a backdated stock adjustment.
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

    if (
        latest_movement
        and movement_date < latest_movement.movement_date
    ):
        raise ValidationError(
            f"Adjustment date cannot be earlier than "
            f"the latest stock movement date "
            f"({latest_movement.movement_date})."
        )


@transaction.atomic
def process_stock_adjustment(
    *,
    adjustment,
):
    """
    Apply a stock adjustment atomically.

    Rules:
    - StockBalance is the source of truth.
    - StockBalance is locked during calculation.
    - Quantity must be positive.
    - DECREASE cannot make stock negative.
    - Backdated adjustments are rejected.
    - Original stock movements are never modified.
    - A new ADJUSTMENT ledger entry is created.
    """

    # Lock the adjustment itself.
    adjustment = (
        StockAdjustment.objects
        .select_for_update()
        .select_related(
            "branch",
            "product",
            "created_by",
        )
        .get(pk=adjustment.pk)
    )

    quantity = Decimal(adjustment.quantity)

    if quantity <= 0:
        raise ValidationError(
            "Adjustment quantity must be greater than zero."
        )

    if adjustment.adjustment_type not in {
        StockAdjustment.AdjustmentType.INCREASE,
        StockAdjustment.AdjustmentType.DECREASE,
    }:
        raise ValidationError(
            "Invalid adjustment type."
        )

    if not adjustment.reason or not adjustment.reason.strip():
        raise ValidationError(
            "Adjustment reason is required."
        )

    _validate_movement_date(
        branch=adjustment.branch,
        product=adjustment.product,
        movement_date=adjustment.adjustment_date,
    )

    balance = _get_or_create_locked_balance(
        branch=adjustment.branch,
        product=adjustment.product,
    )

    balance_before = balance.quantity

    if (
        adjustment.adjustment_type
        == StockAdjustment.AdjustmentType.INCREASE
    ):
        ledger_quantity = quantity
        balance_after = balance_before + quantity

    else:
        if quantity > balance_before:
            raise ValidationError(
                f"Adjustment quantity cannot be greater "
                f"than current stock. "
                f"Available stock: {balance_before}"
            )

        ledger_quantity = -quantity
        balance_after = balance_before - quantity

    # Update current stock.
    balance.quantity = balance_after

    balance.save(
        update_fields=[
            "quantity",
            "updated_at",
        ]
    )

    # Create immutable ledger entry.
    ledger = StockLedger.objects.create(
        branch=adjustment.branch,
        product=adjustment.product,
        movement_type=StockLedger.MovementType.ADJUSTMENT,
        quantity=ledger_quantity,
        balance_before=balance_before,
        balance_after=balance_after,
        reference_type=StockLedger.ReferenceType.STOCK_ADJUSTMENT,
        reference_id=adjustment.id,
        movement_date=adjustment.adjustment_date,
        remarks=adjustment.reason.strip(),
        created_by=adjustment.created_by,
    )

    return {
        "adjustment": adjustment,
        "ledger": ledger,
        "previous_stock": balance_before,
        "adjustment_quantity": quantity,
        "adjustment_type": adjustment.adjustment_type,
        "new_stock": balance_after,
    }