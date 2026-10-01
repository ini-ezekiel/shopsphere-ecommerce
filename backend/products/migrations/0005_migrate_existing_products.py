from django.db import migrations


def migrate_existing_products(apps, schema_editor):
    Product = apps.get_model("products", "Product")
    ProductVariant = apps.get_model(
        "products",
        "ProductVariant",
    )
    Inventory = apps.get_model("products", "Inventory")

    for product in Product.objects.all().iterator():
        variant, created = ProductVariant.objects.get_or_create(
            product_id=product.id,
            attributes={},
            defaults={
                "name": "Default",
                "sku": product.sku,
                "price": product.price,
                "is_active": product.is_active,
            },
        )

        Inventory.objects.update_or_create(
            variant_id=variant.id,
            defaults={
                "quantity": product.stock_quantity,
                "reserved_quantity": 0,
            },
        )


class Migration(migrations.Migration):

    dependencies = [
        (
            "products",
            "0004_remove_category_brand_product_brand",
        ),
    ]

    operations = [
        migrations.RunPython(
            migrate_existing_products,
            reverse_code=migrations.RunPython.noop,
        ),
    ]