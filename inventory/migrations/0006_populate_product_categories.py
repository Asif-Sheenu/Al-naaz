
from django.db import migrations


def populate_product_categories(apps, schema_editor):
    Product = apps.get_model("inventory", "Product")
    ProductCategory = apps.get_model("inventory", "ProductCategory")

    db_alias = schema_editor.connection.alias

    products = (
        Product.objects.using(db_alias)
        .exclude(category="")
        .order_by("id")
    )

    for product in products.iterator():
        category_name = (product.category or "").strip()

        if not category_name:
            continue

        category, _ = (
            ProductCategory.objects.using(db_alias)
            .get_or_create(
                name=category_name,
                defaults={"is_active": True},
            )
        )

        Product.objects.using(db_alias).filter(
            pk=product.pk
        ).update(product_category_id=category.pk)


def reverse_populate_product_categories(apps, schema_editor):
    Product = apps.get_model("inventory", "Product")
    db_alias = schema_editor.connection.alias

    # Remove the links created by this migration.
    # Keep the original category text unchanged.
    Product.objects.using(db_alias).update(
        product_category_id=None
    )


class Migration(migrations.Migration):

    dependencies = [
        (
            "inventory",
            "0005_productcategory_product_product_category",
        ),
    ]

    operations = [
        migrations.RunPython(
            populate_product_categories,
            reverse_populate_product_categories,
        ),
    ]
