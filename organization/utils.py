def get_user_branches(user):

    if user.is_superuser:
        from .models import Branch
        return Branch.objects.filter(is_active=True)

    return user.branches.filter(
        is_active=True
    )