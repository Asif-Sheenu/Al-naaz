from decimal import Decimal

from django.db import transaction

from expenses.models import (
    DailySales,
    DailySalesPayment,
)


@transaction.atomic
def create_daily_sales(
    *,
    branch,
    business_date,
    payments,
    created_by,
):
    total_gross = sum(
        payment["amount"]
        for payment in payments
    )

    if total_gross <= Decimal("0.00"):
        raise ValueError(
            "Total sales amount must be greater than zero."
        )

    daily_sales = DailySales.objects.create(
        branch=branch,
        business_date=business_date,
        total_gross=total_gross,
        status=DailySales.Status.DRAFT,
        created_by=created_by,
    )

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

    return daily_sales