                                               

import django.core.validators
import django.db.models.deletion
import uuid
from decimal import Decimal
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Brand',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('name', models.CharField(db_index=True, max_length=100, unique=True, verbose_name='Name')),
                ('slug', models.SlugField(max_length=120, unique=True, verbose_name='Slug')),
                ('description', models.TextField(blank=True, verbose_name='Description')),
                ('is_active', models.BooleanField(db_index=True, default=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'verbose_name': 'Brand',
                'verbose_name_plural': 'Brands',
                'db_table': 'products_brand',
                'ordering': ['name'],
            },
        ),
        migrations.CreateModel(
            name='ProductAttribute',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('name', models.CharField(max_length=100, unique=True, verbose_name='Name')),
            ],
            options={
                'verbose_name': 'Product Attribute',
                'db_table': 'products_attribute',
                'ordering': ['name'],
            },
        ),
        migrations.CreateModel(
            name='ProductAttributeValue',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('value', models.CharField(max_length=100, verbose_name='Value')),
                ('attribute', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='values', to='products.productattribute')),
            ],
            options={
                'verbose_name': 'Attribute Value',
                'db_table': 'products_attribute_value',
                'ordering': ['attribute', 'value'],
            },
        ),
        migrations.CreateModel(
            name='ProductCategory',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('name', models.CharField(max_length=100, verbose_name='Name')),
                ('slug', models.SlugField(max_length=120, unique=True, verbose_name='Slug')),
                ('is_active', models.BooleanField(db_index=True, default=True)),
                ('ordering', models.PositiveIntegerField(default=0, verbose_name='Display Order')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('parent', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='subcategories', to='products.productcategory', verbose_name='Parent Category')),
            ],
            options={
                'verbose_name': 'Product Category',
                'verbose_name_plural': 'Product Categories',
                'db_table': 'products_category',
                'ordering': ['ordering', 'name'],
            },
        ),
        migrations.CreateModel(
            name='Product',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('name', models.CharField(db_index=True, max_length=255)),
                ('slug', models.SlugField(max_length=255, unique=True)),
                ('description', models.TextField(blank=True)),
                ('price', models.DecimalField(decimal_places=2, max_digits=14, validators=[django.core.validators.MinValueValidator(Decimal('0.00'))], verbose_name='Base Price')),
                ('promo_price', models.DecimalField(blank=True, decimal_places=2, help_text='If set, overrides base price for all non-variant purchases.', max_digits=14, null=True, validators=[django.core.validators.MinValueValidator(Decimal('0.00'))], verbose_name='Promo Price')),
                ('currency', models.CharField(default='USD', max_length=3)),
                ('is_active', models.BooleanField(db_index=True, default=True)),
                ('is_visible', models.BooleanField(db_index=True, default=True)),
                ('has_variants', models.BooleanField(db_index=True, default=False, help_text='True when product has SKU-level variants.', verbose_name='Has Variants')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('brand', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='products', to='products.brand', verbose_name='Brand')),
                ('category', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='products', to='products.productcategory', verbose_name='Category')),
            ],
            options={
                'verbose_name': 'Product',
                'verbose_name_plural': 'Products',
                'db_table': 'products_product',
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='ProductImage',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('image_url', models.URLField(max_length=500, verbose_name='Image URL')),
                ('alt_text', models.CharField(blank=True, max_length=255)),
                ('is_primary', models.BooleanField(db_index=True, default=False)),
                ('ordering', models.PositiveIntegerField(default=0)),
                ('product', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='images', to='products.product')),
            ],
            options={
                'verbose_name': 'Product Image',
                'verbose_name_plural': 'Product Images',
                'db_table': 'products_image',
                'ordering': ['ordering'],
            },
        ),
        migrations.CreateModel(
            name='ProductVariant',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('sku', models.CharField(db_index=True, max_length=100, unique=True, verbose_name='SKU')),
                ('stock', models.PositiveIntegerField(default=0, help_text='Available units.  Updated atomically via F() expressions.', verbose_name='Stock')),
                ('price_override', models.DecimalField(blank=True, decimal_places=2, help_text='If set, replaces product base price for this SKU.', max_digits=14, null=True, validators=[django.core.validators.MinValueValidator(Decimal('0.00'))], verbose_name='Price Override')),
                ('promo_price', models.DecimalField(blank=True, decimal_places=2, max_digits=14, null=True, validators=[django.core.validators.MinValueValidator(Decimal('0.00'))], verbose_name='Promo Price Override')),
                ('is_active', models.BooleanField(db_index=True, default=True)),
                ('attributes_hash', models.CharField(db_index=True, editable=False, max_length=64, verbose_name='Attributes Hash')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('product', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='variants', to='products.product')),
            ],
            options={
                'verbose_name': 'Product Variant',
                'verbose_name_plural': 'Product Variants',
                'db_table': 'products_variant',
            },
        ),
        migrations.CreateModel(
            name='ProductVariantAttributeValue',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('attribute_value', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='variant_links', to='products.productattributevalue')),
                ('variant', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='attribute_values', to='products.productvariant')),
            ],
            options={
                'verbose_name': 'Variant Attribute Value',
                'db_table': 'products_variant_attribute_value',
            },
        ),
        migrations.AddIndex(
            model_name='productattributevalue',
            index=models.Index(fields=['attribute'], name='attr_value_attribute_idx'),
        ),
        migrations.AddConstraint(
            model_name='productattributevalue',
            constraint=models.UniqueConstraint(fields=('attribute', 'value'), name='unique_attribute_value_per_attribute'),
        ),
        migrations.AddIndex(
            model_name='productcategory',
            index=models.Index(fields=['parent', 'is_active'], name='category_parent_active_idx'),
        ),
        migrations.AddConstraint(
            model_name='productcategory',
            constraint=models.CheckConstraint(condition=models.Q(('parent__isnull', True), models.Q(('parent', models.F('pk')), _negated=True), _connector='OR'), name='category_not_self_parent'),
        ),
        migrations.AddIndex(
            model_name='product',
            index=models.Index(fields=['category', 'is_active', 'is_visible'], name='prod_cat_active_visible_idx'),
        ),
        migrations.AddIndex(
            model_name='product',
            index=models.Index(fields=['brand', 'is_active'], name='product_brand_active_idx'),
        ),
        migrations.AddConstraint(
            model_name='product',
            constraint=models.CheckConstraint(condition=models.Q(('price__gte', 0)), name='product_price_gte_0'),
        ),
        migrations.AddConstraint(
            model_name='product',
            constraint=models.CheckConstraint(condition=models.Q(('promo_price__isnull', True), ('promo_price__gte', 0), _connector='OR'), name='prod_promo_price_gte_0'),
        ),
        migrations.AddConstraint(
            model_name='productimage',
            constraint=models.UniqueConstraint(condition=models.Q(('is_primary', True)), fields=('product',), name='one_primary_image_per_product'),
        ),
        migrations.AddIndex(
            model_name='productvariant',
            index=models.Index(fields=['product', 'is_active'], name='variant_product_active_idx'),
        ),
        migrations.AddConstraint(
            model_name='productvariant',
            constraint=models.UniqueConstraint(fields=('product', 'attributes_hash'), name='unique_variant_per_product_attributes'),
        ),
        migrations.AddConstraint(
            model_name='productvariant',
            constraint=models.CheckConstraint(condition=models.Q(('stock__gte', 0)), name='variant_stock_gte_0'),
        ),
        migrations.AddConstraint(
            model_name='productvariant',
            constraint=models.CheckConstraint(condition=models.Q(('price_override__isnull', True), ('price_override__gte', 0), _connector='OR'), name='variant_price_override_gte_0_or_null'),
        ),
        migrations.AddIndex(
            model_name='productvariantattributevalue',
            index=models.Index(fields=['variant'], name='vav_variant_idx'),
        ),
        migrations.AddConstraint(
            model_name='productvariantattributevalue',
            constraint=models.UniqueConstraint(fields=('variant', 'attribute_value'), name='unique_attr_value_per_variant'),
        ),
    ]
