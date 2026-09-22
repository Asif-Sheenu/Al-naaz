from datetime import timedelta
from decimal import Decimal

from django.db import transaction

from expenses.models import (
    DeliveryPartner,
    DeliveryPartnerCommissionRate,
)


@transaction.atomic
def change_commission_rate(
    *,
    delivery_partner,
    commission_rate,
    effective_from,
    created_by,
):
    commission_rate = Decimal(commission_rate)

    if commission_rate < Decimal("0.00"):
        raise ValueError(
            "Commission rate cannot be negative."
        )

    if commission_rate > Decimal("100.00"):
        raise ValueError(
            "Commission rate cannot exceed 100%."
        )

    delivery_partner = (
        DeliveryPartner.objects
        .select_for_update()
        .get(pk=delivery_partner.pk)
    )

    existing_rates = (
        DeliveryPartnerCommissionRate.objects
        .select_for_update()
        .filter(
            delivery_partner=delivery_partner,
            effective_from__lte=effective_from,
        )
        .order_by("-effective_from")
    )

    current_rate = existing_rates.first()

    if current_rate:

        if current_rate.commission_rate == commission_rate:
            raise ValueError(
                "The new commission rate is the same as "
                "the rate already effective on this date."
            )

        current_rate.effective_to = (
            effective_from - timedelta(days=1)
        )

        current_rate.save(
            update_fields=["effective_to"]
        )

    new_rate = DeliveryPartnerCommissionRate.objects.create(
        delivery_partner=delivery_partner,
        commission_rate=commission_rate,
        effective_from=effective_from,
        effective_to=None,
        created_by=created_by,
    )

    return new_rate