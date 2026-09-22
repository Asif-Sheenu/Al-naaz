from django.db import transaction,models
from decimal import Decimal
from expenses.models import (
    DailySales,
    DailySalesPayment,
    FinancialAccount,
    FinancialTransaction,
    Receivable,
    DeliveryPartnerCommissionRate,
)


@transaction.atomic
def post_daily_sales(
    *,
    daily_sales: DailySales,
    created_by,
):
    # --------------------------------------------------
    # 1. Make sure the sale is still a DRAFT
    # --------------------------------------------------

    if daily_sales.status == DailySales.Status.POSTED:
        raise ValueError(
            "Daily sales has already been posted."
        )

    # --------------------------------------------------
    # 2. Lock the DailySales row
    # --------------------------------------------------

    daily_sales = (
        DailySales.objects
        .select_for_update()
        .select_related("branch")
        .get(pk=daily_sales.pk)
    )

    # --------------------------------------------------
    # 3. Double-check status after locking
    # --------------------------------------------------

    if daily_sales.status == DailySales.Status.POSTED:
        raise ValueError(
            "Daily sales has already been posted."
        )

    # --------------------------------------------------
    # 4. Get all payment entries
    # --------------------------------------------------

    payments = list(
        daily_sales.payments.all()
    )

    if not payments:
        raise ValueError(
            "Daily sales has no payment entries."
        )

    # --------------------------------------------------
    # 5. Find the financial accounts
    # --------------------------------------------------

    accounts = FinancialAccount.objects.filter(
        branch=daily_sales.branch,
        is_active=True,
    )

    cash_account = accounts.filter(
        account_purpose=FinancialAccount.AccountPurpose.CASH
    ).first()

    upi_account = accounts.filter(
        account_purpose=FinancialAccount.AccountPurpose.UPI
    ).first()

    card_receivable_account = accounts.filter(
        account_purpose=(
            FinancialAccount.AccountPurpose.CARD_RECEIVABLE
        )
    ).first()

    food_delivery_account = accounts.filter(
        account_purpose=(
            FinancialAccount.AccountPurpose.FOOD_DELIVERY_RECEIVABLE
        )
    ).first()

    # --------------------------------------------------
    # 6. Process each payment
    # --------------------------------------------------

    for payment in payments:

        account = None

        if payment.payment_method == DailySalesPayment.PaymentMethod.CASH:
            account = cash_account

        elif payment.payment_method == DailySalesPayment.PaymentMethod.UPI:
            account = upi_account

        elif payment.payment_method == DailySalesPayment.PaymentMethod.CARD:
            account = card_receivable_account

        elif (
            payment.payment_method
            == DailySalesPayment.PaymentMethod.FOOD_DELIVERY
        ):
            account = food_delivery_account

        if account is None:
            raise ValueError(
                f"No financial account configured for "
                f"payment method '{payment.payment_method}'."
            )

        # --------------------------------------------------
        # Create financial transaction
        # --------------------------------------------------

        FinancialTransaction.objects.create(
            branch=daily_sales.branch,
            account=account,
            transaction_type=(
                FinancialTransaction.TransactionType.REVENUE
            ),
            direction=(
                FinancialTransaction.Direction.IN
            ),
            amount=payment.amount,
            transaction_date=daily_sales.business_date,
            description=(
                f"Daily sales - "
                f"{payment.payment_method}"
            ),
            reference=f"DAILY-SALES-{daily_sales.id}",
            created_by=created_by,
        )

        if payment.payment_method in {
            DailySalesPayment.PaymentMethod.CARD,
            DailySalesPayment.PaymentMethod.FOOD_DELIVERY,
        }:

            commission_rate = Decimal("0.00")
            commission_amount = Decimal("0.00")
            expected_net_amount = payment.amount
            delivery_partner = None

            # ----------------------------------------------
            # Food delivery commission
            # ----------------------------------------------

            if (
                payment.payment_method
                == DailySalesPayment.PaymentMethod.FOOD_DELIVERY
            ):

                delivery_partner = payment.delivery_partner

                if delivery_partner is None:
                    raise ValueError(
                        "Delivery partner is required for "
                        "food delivery payments."
                    )

                if delivery_partner.branch_id != daily_sales.branch_id:
                    raise ValueError(
                        "Delivery partner must belong to the same "
                        "branch as the daily sales."
                    )

                rate = (
                    DeliveryPartnerCommissionRate.objects
                    .filter(
                        delivery_partner=delivery_partner,
                        effective_from__lte=daily_sales.business_date,
                    )
                    .filter(
                        models.Q(effective_to__isnull=True)
                        | models.Q(
                            effective_to__gte=daily_sales.business_date
                        )
                    )
                    .order_by("-effective_from")
                    .first()
                )

                if rate is None:
                    raise ValueError(
                        f"No commission rate configured for "
                        f"{delivery_partner.name} on "
                        f"{daily_sales.business_date}."
                    )

                commission_rate = rate.commission_rate

                commission_amount = (
                    payment.amount
                    * commission_rate
                    / Decimal("100.00")
                )

                expected_net_amount = (
                    payment.amount
                    - commission_amount
                )

            # ----------------------------------------------
            # Create receivable
            # ----------------------------------------------

            Receivable.objects.create(
                branch=daily_sales.branch,
                daily_sales_payment=payment,
                receivable_account=account,
                platform=payment.platform,
                delivery_partner=delivery_partner,
                gross_amount=payment.amount,
                commission_rate=commission_rate,
                commission_amount=commission_amount,
                expected_net_amount=expected_net_amount,
                settled_amount=Decimal("0.00"),
                outstanding_amount=payment.amount,
                status=Receivable.Status.PENDING,
                business_date=daily_sales.business_date,
                created_by=created_by,
            )

    # --------------------------------------------------
    # 7. Mark Daily Sales as POSTED
    # --------------------------------------------------

    daily_sales.status = DailySales.Status.POSTED
    daily_sales.save(
        update_fields=[
            "status",
            "updated_at",
        ]
    )

    return daily_sales