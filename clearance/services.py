from decimal import Decimal, InvalidOperation

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Sum
from django.utils import timezone

from .models import IssuedItem, ClearancePayment


ZERO = Decimal("0.00")


def _to_decimal(value, field_name):
    """Convert a value to Decimal and reject invalid monetary values."""

    try:
        amount = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        raise ValidationError({
            field_name: "Enter a valid monetary amount."
        })

    if not amount.is_finite():
        raise ValidationError({
            field_name: "Amount must be a finite number."
        })

    return amount


def get_clearance_balance(issued_item):
    """
    Return the outstanding balance for a single item.

    Only finally approved items contribute to the employee's
    confirmed clearance balance.
    """

    if issued_item.approval_status != IssuedItem.ApprovalStatus.APPROVED:
        return ZERO

    total_paid = (
        ClearancePayment.objects
        .filter(issued_item=issued_item)
        .aggregate(total=Sum("amount"))["total"]
        or ZERO
    )

    balance = issued_item.employee_payable - total_paid

    return max(balance, ZERO)


def issue_item(
    *,
    employee,
    item_name,
    quantity,
    unit_value,
    employee_payable,
    issued_by,
    issued_date=None,
    notes="",
):
    """
    Create a clearance item and automatically satisfy the approval
    stage associated with the creator's role.

    STAFF:
        PENDING_MANAGER

    MANAGER:
        Manager stage satisfied -> PENDING_ADMIN

    ADMIN:
        Admin stage satisfied -> PENDING_MANAGER
    """

    if employee is None:
        raise ValidationError({
            "employee": "An employee is required."
        })

    if issued_by is None:
        raise ValidationError({
            "issued_by": "An issuing user is required."
        })

    if not isinstance(item_name, str) or not item_name.strip():
        raise ValidationError({
            "item_name": "Item name is required."
        })

    if isinstance(quantity, bool):
        raise ValidationError({
            "quantity": "Quantity must be a positive integer."
        })

    try:
        quantity = int(quantity)
    except (TypeError, ValueError, OverflowError):
        raise ValidationError({
            "quantity": "Quantity must be a positive integer."
        })

    if quantity < 1:
        raise ValidationError({
            "quantity": "Quantity must be at least 1."
        })

    unit_value = _to_decimal(unit_value, "unit_value")
    employee_payable = _to_decimal(
        employee_payable,
        "employee_payable",
    )

    if unit_value < ZERO:
        raise ValidationError({
            "unit_value": "Unit value cannot be negative."
        })

    if employee_payable < ZERO:
        raise ValidationError({
            "employee_payable": "Employee payable cannot be negative."
        })

    if issued_date is None:
        issued_date = timezone.localdate()

    # Determine which approval stage the creator is authorized
    # to satisfy automatically.
    role = getattr(issued_by, "role", None)

    is_admin = (
        role == "ADMIN"
        or getattr(issued_by, "is_superuser", False)
    )

    is_manager = role == "MANAGER"

    manager_approved_by = None
    manager_approved_at = None

    admin_approved_by = None
    admin_approved_at = None

    if is_admin:
        # Admin stage is satisfied by the creating admin.
        approval_status = (
            IssuedItem.ApprovalStatus.PENDING_MANAGER
        )
        admin_approved_by = issued_by
        admin_approved_at = timezone.now()

    elif is_manager:
        # Manager stage is satisfied by the creating manager.
        approval_status = (
            IssuedItem.ApprovalStatus.PENDING_ADMIN
        )
        manager_approved_by = issued_by
        manager_approved_at = timezone.now()

    else:
        # Staff-created items require both approval stages.
        approval_status = (
            IssuedItem.ApprovalStatus.PENDING_MANAGER
        )

    return IssuedItem.objects.create(
        employee=employee,
        item_name=item_name.strip(),
        quantity=quantity,
        unit_value=unit_value,
        employee_payable=employee_payable,
        issued_by=issued_by,
        issued_date=issued_date,
        notes=notes,
        approval_status=approval_status,
        manager_approved_by=manager_approved_by,
        manager_approved_at=manager_approved_at,
        admin_approved_by=admin_approved_by,
        admin_approved_at=admin_approved_at,
    )

@transaction.atomic
def approve_by_manager(*, issued_item_id, approved_by):
    """
    Record manager approval.

    If the admin stage has already been satisfied, the item becomes
    APPROVED. Otherwise, it moves to PENDING_ADMIN.
    """

    if approved_by is None:
        raise ValidationError({
            "approved_by": "An approving user is required."
        })

    item = (
        IssuedItem.objects
        .select_for_update()
        .filter(pk=issued_item_id)
        .first()
    )

    if item is None:
        raise ValidationError({
            "issued_item": "Issued item not found."
        })

    if (
        item.approval_status
        != IssuedItem.ApprovalStatus.PENDING_MANAGER
    ):
        raise ValidationError({
            "approval_status": (
                "This item is not awaiting manager approval."
            )
        })

    if item.issued_by_id == approved_by.pk:
        raise ValidationError({
            "approved_by": (
                "The issuing user cannot approve their own item."
            )
        })

    item.manager_approved_by = approved_by
    item.manager_approved_at = timezone.now()
    item.rejection_reason = ""

    if item.admin_approved_by_id is not None:
        # The admin stage was already satisfied.
        item.approval_status = (
            IssuedItem.ApprovalStatus.APPROVED
        )
    else:
        # Admin approval is still required.
        item.approval_status = (
            IssuedItem.ApprovalStatus.PENDING_ADMIN
        )

    item.save(
        update_fields=[
            "approval_status",
            "manager_approved_by",
            "manager_approved_at",
            "rejection_reason",
            "updated_at",
        ]
    )

    return item

@transaction.atomic
def approve_by_admin(*, issued_item_id, approved_by):
    """
    Record final admin approval.

    If the manager stage has already been satisfied, the item becomes
    APPROVED. Otherwise, it moves to PENDING_MANAGER.
    """

    if approved_by is None:
        raise ValidationError({
            "approved_by": "An approving user is required."
        })

    item = (
        IssuedItem.objects
        .select_for_update()
        .filter(pk=issued_item_id)
        .first()
    )

    if item is None:
        raise ValidationError({
            "issued_item": "Issued item not found."
        })

    if (
        item.approval_status
        != IssuedItem.ApprovalStatus.PENDING_ADMIN
    ):
        raise ValidationError({
            "approval_status": (
                "This item is not awaiting admin approval."
            )
        })

    if item.issued_by_id == approved_by.pk:
        raise ValidationError({
            "approved_by": (
                "The issuing user cannot approve their own item."
            )
        })

    if item.manager_approved_by_id == approved_by.pk:
        raise ValidationError({
            "approved_by": (
                "The manager approver cannot give final approval."
            )
        })

    item.admin_approved_by = approved_by
    item.admin_approved_at = timezone.now()
    item.rejection_reason = ""

    if item.manager_approved_by_id is not None:
        # The manager stage was already satisfied.
        item.approval_status = (
            IssuedItem.ApprovalStatus.APPROVED
        )
    else:
        # Manager approval is still required.
        item.approval_status = (
            IssuedItem.ApprovalStatus.PENDING_MANAGER
        )

    item.save(
        update_fields=[
            "approval_status",
            "admin_approved_by",
            "admin_approved_at",
            "rejection_reason",
            "updated_at",
        ]
    )

    return item

@transaction.atomic
def reject_issued_item(
    *,
    issued_item_id,
    rejected_by,
    rejection_reason,
    stage,
):
    """
    Reject an item at the manager or admin approval stage.

    Physical return handling is intentionally not implemented yet.
    """

    if rejected_by is None:
        raise ValidationError({
            "rejected_by": "A rejecting user is required."
        })

    if not isinstance(rejection_reason, str) or not rejection_reason.strip():
        raise ValidationError({
            "rejection_reason": "A rejection reason is required."
        })

    if stage not in {"MANAGER", "ADMIN"}:
        raise ValidationError({
            "stage": "Stage must be MANAGER or ADMIN."
        })

    item = (
        IssuedItem.objects
        .select_for_update()
        .filter(pk=issued_item_id)
        .first()
    )

    if item is None:
        raise ValidationError({
            "issued_item": "Issued item not found."
        })

    expected_status = (
        IssuedItem.ApprovalStatus.PENDING_MANAGER
        if stage == "MANAGER"
        else IssuedItem.ApprovalStatus.PENDING_ADMIN
    )

    if item.approval_status != expected_status:
        raise ValidationError({
            "approval_status": (
                f"This item is not awaiting {stage.lower()} review."
            )
        })

    if item.issued_by_id == rejected_by.pk:
        raise ValidationError({
            "rejected_by": "The issuing user cannot reject their own item."
        })

    if (
        stage == "ADMIN"
        and item.manager_approved_by_id == rejected_by.pk
    ):
        raise ValidationError({
            "rejected_by": "The manager approver cannot act as final admin."
        })

    item.approval_status = IssuedItem.ApprovalStatus.REJECTED
    item.rejection_reason = rejection_reason.strip()

    item.save(update_fields=[
        "approval_status",
        "rejection_reason",
        "updated_at",
    ])

    return item


@transaction.atomic
def record_clearance_payment(
    *,
    issued_item_id,
    amount,
    payment_method,
    recorded_by,
    payment_date=None,
    reference="",
    notes="",
):
    """
    Record a payment against an approved item.

    Row locking prevents concurrent payments from exceeding
    the outstanding balance when using a database that supports
    SELECT FOR UPDATE, such as PostgreSQL.
    """

    amount = _to_decimal(amount, "amount")

    if amount <= ZERO:
        raise ValidationError({
            "amount": "Payment amount must be greater than zero."
        })

    if recorded_by is None:
        raise ValidationError({
            "recorded_by": "A recording user is required."
        })

    item = (
        IssuedItem.objects
        .select_for_update()
        .filter(pk=issued_item_id)
        .first()
    )

    if item is None:
        raise ValidationError({
            "issued_item": "Issued item not found."
        })

    if item.approval_status != IssuedItem.ApprovalStatus.APPROVED:
        raise ValidationError({
            "issued_item": (
                "Payments are allowed only after final admin approval."
            )
        })

    if payment_date is None:
        payment_date = timezone.localdate()

    outstanding = get_clearance_balance(item)

    if amount > outstanding:
        raise ValidationError({
            "amount": (
                f"Payment exceeds the outstanding balance of "
                f"{outstanding}."
            )
        })

    return ClearancePayment.objects.create(
        issued_item=item,
        amount=amount,
        payment_method=payment_method,
        recorded_by=recorded_by,
        payment_date=payment_date,
        reference=reference,
        notes=notes,
    )