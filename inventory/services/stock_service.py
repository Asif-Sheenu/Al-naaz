from ..models import Product, StockBalance, StockLedger

from core.cache.keys import inventory_stock
from core.cache.service import get as cache_get
from core.cache.service import set as cache_set
from core.cache.constants import (
    INVENTORY_STOCK_CACHE_TIMEOUT,
)


def get_live_stock(params=None):

    params = params or {}

    search = params.get("search")
    category = params.get("category")
    status = params.get("status")
    branch = params.get("branch")

    # ------------------------------------------------------------
    # CACHE
    # ------------------------------------------------------------

    cache_key = inventory_stock(
        branch_id=branch,
        search=search,
        category=category,
        status=status,
    )

    cached_data = cache_get(cache_key)

    if cached_data is not None:
        return cached_data

    # ------------------------------------------------------------
    # PRODUCTS
    # ------------------------------------------------------------

    products = (
        Product.objects
        .filter(is_active=True)
        .order_by("name")
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

    # ------------------------------------------------------------
    # STOCK BALANCES
    # ------------------------------------------------------------

    # If a branch is supplied, only return stock
    # for that branch.
    #
    # If no branch is supplied, calculate total
    # stock across branches.

    stock_balances = (
        StockBalance.objects
        .select_related(
            "product",
            "branch",
        )
    )

    if branch:
        stock_balances = stock_balances.filter(
            branch_id=branch
        )

    # ------------------------------------------------------------
    # BUILD STOCK LOOKUP
    # ------------------------------------------------------------

    stock_lookup = {}

    for balance in stock_balances:

        product_id = balance.product_id

        stock_lookup[product_id] = (
            stock_lookup.get(product_id, 0)
            + balance.quantity
        )

    # ------------------------------------------------------------
    # BUILD RESPONSE
    # ------------------------------------------------------------

    stock_data = []

    for product in products:

        current_stock = stock_lookup.get(
            product.id,
            0
        )

        if current_stock <= 0:
            stock_status = "OUT_OF_STOCK"

        elif current_stock <= product.minimum_stock:
            stock_status = "LOW_STOCK"

        else:
            stock_status = "GOOD"

        if (
            status
            and status.upper() != stock_status
        ):
            continue

        stock_data.append({
            "product": product.id,
            "product_name": product.name,
            "unit": product.unit,
            "current_stock": current_stock,
            "minimum_stock": product.minimum_stock,
            "status": stock_status,
        })

    # ------------------------------------------------------------
    # STORE IN CACHE
    # ------------------------------------------------------------

    cache_set(
        cache_key,
        stock_data,
        INVENTORY_STOCK_CACHE_TIMEOUT,
    )

    return stock_data


def get_stock_ledger(params=None):

    params = params or {}

    product = params.get("product")
    movement_type = params.get("movement_type")
    start_date = params.get("start_date")
    end_date = params.get("end_date")
    branch = params.get("branch")

    queryset = (
        StockLedger.objects
        .select_related(
            "branch",
            "product",
        )
        .order_by(
            "-movement_date",
            "-id",
        )
    )

    if branch:
        queryset = queryset.filter(
            branch_id=branch
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