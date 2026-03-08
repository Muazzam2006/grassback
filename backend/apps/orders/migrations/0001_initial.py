                                               

import django.core.validators
import django.db.models.deletion
import uuid
from decimal import Decimal
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('delivery', '0001_initial'),
        ('products', '0001_initial'),
        ('reservations', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Order',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('status', models.CharField(choices=[('CREATED', 'Created'), ('RESERVED', 'Reserved'), ('CONFIRMED', 'Confirmed'), ('SHIPPED', 'Shipped'), ('DELIVERED', 'Delivered'), ('CANCELLED', 'Cancelled')], db_index=True, default='CREATED', max_length=12)),
                ('total_amount', models.DecimalField(decimal_places=2, default=Decimal('0.00'), help_text='Items subtotal (quantity × effective price for each line).', max_digits=14)),
                ('delivery_fee', models.DecimalField(decimal_places=2, default=Decimal('0.00'), help_text='Snapshot of delivery fee at time of checkout.', max_digits=14)),
                ('currency', models.CharField(default='USD', max_length=3)),
                ('created_at', models.DateTimeField(auto_now_add=True, db_index=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('delivery_address', models.ForeignKey(help_text='Mandatory — where COD goods will be delivered.', on_delete=django.db.models.deletion.PROTECT, related_name='orders', to='delivery.deliveryaddress', verbose_name='Delivery Address')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='orders', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'db_table': 'orders_order',
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='OrderItem',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('product_name_snapshot', models.CharField(help_text='Snapshot of product name at time of checkout.', max_length=255)),
                ('product_price_snapshot', models.DecimalField(decimal_places=2, help_text='Snapshot of effective price at time of checkout.', max_digits=14, validators=[django.core.validators.MinValueValidator(Decimal('0.00'))])),
                ('quantity', models.PositiveIntegerField(validators=[django.core.validators.MinValueValidator(1)])),
                ('line_total', models.DecimalField(decimal_places=2, help_text='quantity × product_price_snapshot — snapshotted at checkout.', max_digits=14)),
                ('order', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='items', to='orders.order')),
                ('product', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='order_items', to='products.product')),
                ('reservation', models.ForeignKey(blank=True, help_text='Audit trail: the reservation that was converted into this item.', null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='order_items', to='reservations.reservation', verbose_name='Source Reservation')),
                ('variant', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='order_items', to='products.productvariant', verbose_name='Product Variant (SKU)')),
            ],
            options={
                'db_table': 'orders_order_item',
            },
        ),
        migrations.CreateModel(
            name='OrderLifecycleLog',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('from_status', models.CharField(blank=True, choices=[('CREATED', 'Created'), ('RESERVED', 'Reserved'), ('CONFIRMED', 'Confirmed'), ('SHIPPED', 'Shipped'), ('DELIVERED', 'Delivered'), ('CANCELLED', 'Cancelled')], default='', max_length=12)),
                ('to_status', models.CharField(choices=[('CREATED', 'Created'), ('RESERVED', 'Reserved'), ('CONFIRMED', 'Confirmed'), ('SHIPPED', 'Shipped'), ('DELIVERED', 'Delivered'), ('CANCELLED', 'Cancelled')], max_length=12)),
                ('note', models.CharField(blank=True, default='', max_length=500)),
                ('created_at', models.DateTimeField(auto_now_add=True, db_index=True)),
                ('changed_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='order_lifecycle_actions', to=settings.AUTH_USER_MODEL)),
                ('order', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='lifecycle_logs', to='orders.order')),
            ],
            options={
                'db_table': 'orders_lifecycle_log',
                'ordering': ['created_at'],
            },
        ),
        migrations.AddIndex(
            model_name='order',
            index=models.Index(fields=['user', 'status'], name='order_user_status_idx'),
        ),
        migrations.AddConstraint(
            model_name='order',
            constraint=models.CheckConstraint(condition=models.Q(('total_amount__gte', 0)), name='orders_order_total_amount_gte_0'),
        ),
        migrations.AddConstraint(
            model_name='order',
            constraint=models.CheckConstraint(condition=models.Q(('delivery_fee__gte', 0)), name='orders_order_delivery_fee_gte_0'),
        ),
        migrations.AddIndex(
            model_name='orderitem',
            index=models.Index(fields=['order'], name='order_item_order_idx'),
        ),
        migrations.AddConstraint(
            model_name='orderitem',
            constraint=models.CheckConstraint(condition=models.Q(('quantity__gt', 0)), name='order_item_quantity_gt_0'),
        ),
        migrations.AddConstraint(
            model_name='orderitem',
            constraint=models.CheckConstraint(condition=models.Q(('product_price_snapshot__gte', 0)), name='order_item_price_gte_0'),
        ),
        migrations.AddConstraint(
            model_name='orderitem',
            constraint=models.CheckConstraint(condition=models.Q(('line_total__gte', 0)), name='order_item_line_total_gte_0'),
        ),
        migrations.AddConstraint(
            model_name='orderitem',
            constraint=models.UniqueConstraint(fields=('order', 'product', 'variant'), name='unique_product_variant_per_order'),
        ),
        migrations.AddIndex(
            model_name='orderlifecyclelog',
            index=models.Index(fields=['order', 'created_at'], name='order_log_order_ts_idx'),
        ),
    ]
