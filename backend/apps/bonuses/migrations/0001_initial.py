                                               

import django.core.validators
import uuid
from decimal import Decimal
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Bonus',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('level', models.PositiveIntegerField(validators=[django.core.validators.MinValueValidator(1)])),
                ('bonus_type', models.CharField(choices=[('PERSONAL', 'Personal'), ('TEAM', 'Team')], default='PERSONAL', max_length=10)),
                ('percent_snapshot', models.DecimalField(blank=True, decimal_places=2, help_text='Deprecated in v2. Use applied_value_snapshot instead.', max_digits=5, null=True, validators=[django.core.validators.MinValueValidator(Decimal('0.00'))])),
                ('calculation_type_snapshot', models.CharField(choices=[('PERCENT', 'Percentage'), ('FIXED', 'Fixed Amount')], default='PERCENT', max_length=10, verbose_name='Calculation Type (Snapshot)')),
                ('applied_value_snapshot', models.DecimalField(blank=True, decimal_places=4, help_text='The rule value (% or flat) that produced this bonus amount.', max_digits=12, null=True, validators=[django.core.validators.MinValueValidator(Decimal('0.0000'))], verbose_name='Applied Value (Snapshot)')),
                ('amount', models.DecimalField(decimal_places=2, max_digits=14, validators=[django.core.validators.MinValueValidator(Decimal('0.01'))])),
                ('status', models.CharField(choices=[('PENDING', 'Pending'), ('CONFIRMED', 'Confirmed')], default='PENDING', max_length=10)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
            options={
                'verbose_name': 'Bonus',
                'verbose_name_plural': 'Bonuses',
                'db_table': 'bonuses_bonus',
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='MLMRule',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('agent_status', models.CharField(choices=[('NEW', 'New'), ('BRONZE', 'Bronze'), ('SILVER', 'Silver'), ('GOLD', 'Gold')], max_length=10)),
                ('level', models.PositiveIntegerField(validators=[django.core.validators.MinValueValidator(1)])),
                ('calculation_type', models.CharField(choices=[('PERCENT', 'Percentage'), ('FIXED', 'Fixed Amount')], default='PERCENT', help_text='PERCENT: value% of order total.  FIXED: flat amount per order.', max_length=10, verbose_name='Calculation Type')),
                ('value', models.DecimalField(decimal_places=4, help_text='Percentage (e.g. 5.25) or fixed amount depending on calculation_type.', max_digits=12, validators=[django.core.validators.MinValueValidator(Decimal('0.0000'))], verbose_name='Value')),
                ('is_active', models.BooleanField(default=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
            options={
                'verbose_name': 'MLM Rule',
                'verbose_name_plural': 'MLM Rules',
                'db_table': 'bonuses_mlm_rule',
                'ordering': ['agent_status', 'level'],
            },
        ),
    ]
