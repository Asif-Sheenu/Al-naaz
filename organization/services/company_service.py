from django.db import transaction

from ..models import Company


@transaction.atomic
def create_company(
    *,
    name,
    code,
    address="",
    phone="",
    email="",
):
    return Company.objects.create(
        name=name,
        code=code,
        address=address,
        phone=phone,
        email=email,
    )