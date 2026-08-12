from django.db import transaction
from inventory.models import PurchaseItem

from ..models import Purchase, StockLedger


@transaction.atomic
def process_purchase(purchase):

    for item in purchase.items.select_related("product"):

        # Find the latest stock balance
        last_entry = (
            StockLedger.objects
            .filter(product=item.product)
            .order_by("-id")
            .first()
        )

        current_stock = (
            last_entry.balance_after
            if last_entry
            else 0
        )

        new_stock = current_stock + item.quantity

        StockLedger.objects.create(
            product=item.product,
            movement_type=StockLedger.MovementType.PURCHASE,
            quantity=item.quantity,
            balance_after=new_stock,
            reference_id=purchase.id,
            movement_date=purchase.purchase_date,
            remarks=f"Purchase #{purchase.id}",
        )



def get_supplier_purchase_history(supplier_id):
    return (
        PurchaseItem.objects
        .filter(
            purchase__supplier_id=supplier_id
        )
        .select_related(
            "purchase__supplier",
            "product"
        )
        .order_by(
            "-purchase__purchase_date",
            "-id"
        )
    )        