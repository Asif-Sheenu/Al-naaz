from ..models import Product, StockLedger


def get_live_stock(params=None):

    params = params or {}

    search = params.get("search")
    category = params.get("category")
    status = params.get("status")

    products = Product.objects.filter(
        is_active=True
    )

    # Search by product name
    if search:
        products = products.filter(
            name__icontains=search
        )

    # Filter by category
    if category:
        products = products.filter(
            category__iexact=category
        )

    stock_data = []

    for product in products:

        last_entry = (
            StockLedger.objects
            .filter(product=product)
            .order_by("-id")
            .first()
        )

        current_stock = (
            last_entry.balance_after
            if last_entry
            else 0
        )

        if current_stock <= 0:
            stock_status = "OUT_OF_STOCK"

        elif current_stock <= product.minimum_stock:
            stock_status = "LOW_STOCK"

        else:
            stock_status = "GOOD"

        # Status filter
        if status and status.upper() != stock_status:
            continue

        stock_data.append({
            "product": product.id,
            "product_name": product.name,
            "unit": product.unit,
            "current_stock": current_stock,
            "minimum_stock": product.minimum_stock,
            "status": stock_status,
        })

    return stock_data



# ------------------------------------------------------------------------------------------------------ 


def get_stock_ledger(params=None):

    params = params or {}

    product = params.get("product")
    movement_type = params.get("movement_type")
    start_date = params.get("start_date")
    end_date = params.get("end_date")

    queryset = (
        StockLedger.objects
        .select_related("product")
        .order_by("-movement_date", "-id")
    )

    if product:
        queryset = queryset.filter(
            product_id=product
        )

    if movement_type:
        queryset = queryset.filter(
            movement_type=movement_type.upper()
        )

    if start_date:
        queryset = queryset.filter(
            movement_date__gte=start_date
        )

    if end_date:
        queryset = queryset.filter(
            movement_date__lte=end_date
        )

    return queryset