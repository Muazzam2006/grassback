                                               

import django.core.validators
import django.db.models.deletion
import uuid
from decimal import Decimal
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Withdrawal',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('reference', models.CharField(db_index=True, editable=False, max_length=20, unique=True, verbose_name='Reference')),
                ('amount', models.DecimalField(decimal_places=2, max_digits=14, validators=[django.core.validators.MinValueValidator(Decimal('0.01'))], verbose_name='Amount')),
                ('currency', models.CharField(default='USD', max_length=3, verbose_name='Currency')),
                ('status', models.CharField(choices=[('PENDING', 'Pending'), ('APPROVED', 'Approved'), ('REJECTED', 'Rejected')], db_index=True, default='PENDING', max_length=10, verbose_name='Status')),
                ('rejection_reason', models.TextField(blank=True, verbose_name='Rejection Reason')),
                ('requested_at', models.DateTimeField(auto_now_add=True, db_index=True, verbose_name='Requested At')),
                ('processed_at', models.DateTimeField(blank=True, null=True, verbose_name='Processed At')),
                ('processed_by', models.ForeignKey(blank=True, help_text='Admin user who approved or rejected this request.', null=True, on_delete=django.db.models.deletion.PROTECT, related_name='processed_withdrawals', to=settings.AUTH_USER_MODEL, verbose_name='Processed By')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='withdrawals', to=settings.AUTH_USER_MODEL, verbose_name='User')),
            ],
            options={
                'verbose_name': 'Withdrawal',
                'verbose_name_plural': 'Withdrawals',
                'db_table': 'withdrawals_withdrawal',
                'ordering': ['-requested_at'],
                'indexes': [models.Index(fields=['user', 'status'], name='withdrawal_user_status_idx'), models.Index(fields=['requested_at'], name='withdrawal_requested_at_idx')],
                'constraints': [models.CheckConstraint(condition=models.Q(('amount__gt', 0)), name='withdrawal_amount_gt_0')],
            },
        ),
    ]
