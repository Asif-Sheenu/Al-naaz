from django.db import transaction

from ..models import User


@transaction.atomic
def create_managed_user(
    *,
    username,
    password,
    role,
    email="",
    phone=None,
):
    if role not in {
        User.Roles.MANAGER,
        User.Roles.STAFF,
    }:
        raise ValueError(
            "Only MANAGER or STAFF users can be created "
            "through user management."
        )

    if User.objects.filter(username=username).exists():
        raise ValueError(
            "A user with this username already exists."
        )

    user = User(
        username=username,
        email=email,
        phone=phone,
        role=role,
    )

    user.set_password(password)
    user.save()

    return user