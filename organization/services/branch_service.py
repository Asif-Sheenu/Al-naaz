from django.db import transaction

from ..models import Branch


@transaction.atomic
def create_branch(
    *,
    company,
    name,
    code,
    address="",
    phone="",
    email="",
):
    return Branch.objects.create(
        company=company,
        name=name,
        code=code,
        address=address,
        phone=phone,
        email=email,
    )


@transaction.atomic
def deactivate_branch(branch):
    if not branch.is_active:
        return branch

    branch.is_active = False
    branch.save(update_fields=["is_active", "updated_at"])

    return branch


@transaction.atomic
def activate_branch(branch):
    if branch.is_active:
        return branch

    branch.is_active = True
    branch.save(update_fields=["is_active", "updated_at"])

    return branch