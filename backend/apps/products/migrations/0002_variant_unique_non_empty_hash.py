from django.db import migrations, models


EMPTY_HASH = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"


class Migration(migrations.Migration):

    dependencies = [
        ("products", "0001_initial"),
    ]

    operations = [
        migrations.RemoveConstraint(
            model_name="productvariant",
            name="unique_variant_per_product_attributes",
        ),
        migrations.AddConstraint(
            model_name="productvariant",
            constraint=models.UniqueConstraint(
                condition=~models.Q(attributes_hash=EMPTY_HASH),
                fields=("product", "attributes_hash"),
                name="unique_variant_per_product_attributes",
            ),
        ),
    ]
