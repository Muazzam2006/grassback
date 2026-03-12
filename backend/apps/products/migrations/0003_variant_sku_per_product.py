from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("products", "0002_variant_unique_non_empty_hash"),
    ]

    operations = [
        migrations.AlterField(
            model_name="productvariant",
            name="sku",
            field=models.CharField(db_index=True, max_length=100, verbose_name="SKU"),
        ),
        migrations.AddConstraint(
            model_name="productvariant",
            constraint=models.UniqueConstraint(
                fields=("product", "sku"),
                name="unique_variant_sku_per_product",
            ),
        ),
    ]
