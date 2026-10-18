import logging
from decimal import Decimal

from django.db import transaction

from expenses.models import (
    DailySales,
    DailySalesPayment,
)

from notifications.services.notification_service import (
    notify_admins_and_managers,
)

logger = logging.getLogger(__name__)


def _notify_daily_sales_draft_created(
    *,
    branch,
    daily_sales_id,
    business_date,
    total_gross,
):
    """Notify admins and branch managers about a new sales draft."""
    try:
        notify_admins_and_managers(
            notification_type="INFO",
            title="Daily Sales Draft Created",
            message=(
                f"A daily sales draft has been created for "
                f"{business_date}. "
                f"Total sales: ₹{total_gross}. "
                f"Daily Sales ID: {daily_sales_id}. "
                f"The entry is awaiting posting."
            ),
            module="FINANCE",
            object_id=daily_sales_id,
            branch=branch,
        )
    except Exception:
        logger.exception(
            "Failed to notify about daily sales draft ID %s",
            daily_sales_id,
        )


@transaction.atomic
def create_daily_sales(
    *,
    branch,
    business_date,
    payments,
    created_by,
):
    # 1. Calculate total sales
    total_gross = sum(
        (
            payment["amount"]
            for payment in payments
        ),
        Decimal("0.00"),
    )

    if total_gross <= Decimal("0.00"):
        raise ValueError(
            "Total sales amount must be greater than zero."
        )

    # 2. Create daily sales as DRAFT
    daily_sales = DailySales.objects.create(
        branch=branch,
        business_date=business_date,
        total_gross=total_gross,
        status=DailySales.Status.DRAFT,
        created_by=created_by,
    )

    # 3. Create payment breakdown
    payment_objects = [
        DailySalesPayment(
            daily_sales=daily_sales,
            payment_method=payment["payment_method"],
            amount=payment["amount"],
            delivery_partner=payment.get("delivery_partner"),
            platform=payment.get("platform", ""),
        )
        for payment in payments
    ]

    DailySalesPayment.objects.bulk_create(
        payment_objects
    )

    # 4. Notify only after the transaction commits
    transaction.on_commit(
        lambda: _notify_daily_sales_draft_created(
            branch=daily_sales.branch,
            daily_sales_id=daily_sales.id,
            business_date=daily_sales.business_date,
            total_gross=daily_sales.total_gross,
        )
    )

    return daily_sales