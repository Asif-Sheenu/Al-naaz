from django.db import transaction
from rest_framework.exceptions import ValidationError

from ..models import StockUsage, StockLedger


@transaction.atomic
def process_usage(usage):

    last_entry = (
        StockLedger.objects
        .filter(product=usage.product)
        .order_by("-id")
        .first()
    )

    current_stock = (
        last_entry.balance_after
        if last_entry
        else 0
    )

    if usage.quantity > current_stock:
        raise ValidationError(
            f"Insufficient stock. "
            f"Available stock: {current_stock}"
        )

    new_stock = current_stock - usage.quantity

    StockLedger.objects.create(
        product=usage.product,
        movement_type=StockLedger.MovementType.USAGE,
        quantity=-usage.quantity,
        balance_after=new_stock,
        reference_id=usage.id,
        movement_date=usage.usage_date,
        remarks=f"Usage #{usage.id}",
    )