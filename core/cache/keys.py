def inventory_stock(
    *,
    branch_id=None,
    search=None,
    category=None,
    status=None,
) -> str:
    parts = ["inventory", "stock"]

    if branch_id:
        parts.extend(["branch", str(branch_id)])
    else:
        parts.append("all")

    if search:
        parts.extend(["search", search.strip().lower()])

    if category:
        parts.extend(["category", category.strip().lower()])

    if status:
        parts.extend(["status", status.strip().upper()])

    return ":".join(parts)