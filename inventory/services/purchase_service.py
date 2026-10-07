from decimal import Decimal

from rest_framework.exceptions import ValidationError
from django.db import transaction

from ..models import (
    Purchase,
    StockBalance,
    StockLedger,
    PurchaseItem,
)
from django.db import IntegrityError, transaction
from core.cache.service import delete_pattern

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

        return (
            StockBalance.objects
            .select_for_update()
            .get(
                branch=branch,
                product=product,
            )
        )

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
            f"Purchase date cannot be earlier than the latest "
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
    Create an immutable stock ledger entry.
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
def process_purchase(purchase):
    """
    Add purchased stock to StockBalance and create
    corresponding StockLedger entries.
    """

    # Lock the purchase itself.
    purchase = (
        Purchase.objects
        .select_for_update()
        .get(pk=purchase.pk)
    )

    items = list(
        purchase.items
        .select_related("product")
        .order_by("product_id")
    )

    if not items:
        raise ValidationError(
            "Purchase must contain at least one item."
        )

    # Prevent receiving the same purchase twice.
    already_processed = StockLedger.objects.filter(
        reference_type=StockLedger.ReferenceType.PURCHASE,
        reference_id=purchase.id,
    ).exists()

    if already_processed:
        raise ValidationError(
            f"Purchase #{purchase.id} has already been processed."
        )

    for item in items:

        if item.quantity <= 0:
            raise ValidationError(
                "Purchase quantity must be greater than zero."
            )

        _validate_movement_date(
            branch=purchase.branch,
            product=item.product,
            movement_date=purchase.purchase_date,
            )

        balance = _get_or_create_locked_balance(
            branch=purchase.branch,
            product=item.product,
        )

        balance_before = balance.quantity

        balance_after = (
            balance_before + item.quantity
        )

        balance.quantity = balance_after

        balance.save(
            update_fields=[
                "quantity",
                "updated_at",
            ]
        )

        _write_ledger(
            branch=purchase.branch,
            product=item.product,
            movement_type=StockLedger.MovementType.PURCHASE,
            quantity=item.quantity,
            balance_before=balance_before,
            balance_after=balance_after,
            reference_type=StockLedger.ReferenceType.PURCHASE,
            reference_id=purchase.id,
            movement_date=purchase.purchase_date,
            remarks=f"Purchase #{purchase.id}",
            created_by=purchase.created_by,
        )

    delete_pattern(
        f"inventory:stock:branch:{purchase.branch_id}*"
    )

    return purchase


def get_supplier_purchase_history(supplier_id):
    return (
        PurchaseItem.objects
        .filter(
            purchase__supplier_id=supplier_id
        )
        .select_related(
            "purchase__supplier",
            "product",
        )
        .order_by(
            "-purchase__purchase_date",
            "-id",
        )
    )