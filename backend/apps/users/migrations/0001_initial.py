                                               

import apps.users.managers
import django.db.models.deletion
import django.utils.timezone
import mptt.fields
import uuid
from decimal import Decimal
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('auth', '0012_alter_user_first_name_max_length'),
    ]

    operations = [
        migrations.CreateModel(
            name='User',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('password', models.CharField(max_length=128, verbose_name='password')),
                ('last_login', models.DateTimeField(blank=True, null=True, verbose_name='last login')),
                ('is_superuser', models.BooleanField(default=False, help_text='Designates that this user has all permissions without explicitly assigning them.', verbose_name='superuser status')),
                ('phone', models.CharField(db_index=True, max_length=20, unique=True)),
                ('first_name', models.CharField(max_length=150, verbose_name='First Name')),
                ('last_name', models.CharField(max_length=150, verbose_name='Last Name')),
                ('is_active', models.BooleanField(default=True, help_text='Designates whether this user should be treated as active.', verbose_name='Active')),
                ('is_staff', models.BooleanField(default=False, help_text='Designates whether the user can log into this admin site.', verbose_name='Staff Status')),
                ('date_joined', models.DateTimeField(default=django.utils.timezone.now, verbose_name='Date Joined')),
                ('referral_code', models.CharField(db_index=True, editable=False, help_text='Unique referral code for this agent', max_length=8, unique=True, verbose_name='Referral Code')),
                ('status', models.CharField(choices=[('NEW', 'New'), ('BRONZE', 'Bronze'), ('SILVER', 'Silver'), ('GOLD', 'Gold')], db_index=True, default='NEW', max_length=10, verbose_name='Status')),
                ('personal_turnover', models.DecimalField(decimal_places=2, default=Decimal('0.00'), max_digits=14, verbose_name='Personal Turnover')),
                ('team_turnover', models.DecimalField(decimal_places=2, default=Decimal('0.00'), max_digits=14, verbose_name='Team Turnover')),
                ('bonus_balance', models.DecimalField(decimal_places=2, default=Decimal('0.00'), max_digits=14, verbose_name='Bonus Balance')),
                ('lft', models.PositiveIntegerField(editable=False)),
                ('rght', models.PositiveIntegerField(editable=False)),
                ('tree_id', models.PositiveIntegerField(db_index=True, editable=False)),
                ('level', models.PositiveIntegerField(editable=False)),
                ('groups', models.ManyToManyField(blank=True, help_text='The groups this user belongs to. A user will get all permissions granted to each of their groups.', related_name='user_set', related_query_name='user', to='auth.group', verbose_name='groups')),
                ('parent', mptt.fields.TreeForeignKey(blank=True, help_text='The agent who referred this user (MPTT parent node)', null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='children', to=settings.AUTH_USER_MODEL, verbose_name='Sponsor')),
                ('user_permissions', models.ManyToManyField(blank=True, help_text='Specific permissions for this user.', related_name='user_set', related_query_name='user', to='auth.permission', verbose_name='user permissions')),
            ],
            options={
                'verbose_name': 'User',
                'verbose_name_plural': 'Users',
                'db_table': 'users_user',
            },
            managers=[
                ('objects', apps.users.managers.UserManager()),
            ],
        ),
        migrations.CreateModel(
            name='OTPToken',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('phone', models.CharField(db_index=True, max_length=20)),
                ('code_hash', models.CharField(max_length=64, verbose_name='Code Hash (SHA-256)')),
                ('purpose', models.CharField(choices=[('REGISTER', 'Registration'), ('LOGIN', 'Login'), ('RESET', 'Password Reset')], db_index=True, default='REGISTER', max_length=10)),
                ('is_used', models.BooleanField(db_index=True, default=False)),
                ('attempts', models.PositiveIntegerField(default=0)),
                ('expires_at', models.DateTimeField(db_index=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
            options={
                'verbose_name': 'OTP Token',
                'verbose_name_plural': 'OTP Tokens',
                'db_table': 'users_otp_token',
                'ordering': ['-created_at'],
                'indexes': [models.Index(fields=['phone', 'purpose', 'is_used', 'expires_at'], name='otp_phone_purpose_idx')],
            },
        ),
        migrations.CreateModel(
            name='UserStatusHistory',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('old_status', models.CharField(choices=[('NEW', 'New'), ('BRONZE', 'Bronze'), ('SILVER', 'Silver'), ('GOLD', 'Gold')], max_length=10)),
                ('new_status', models.CharField(choices=[('NEW', 'New'), ('BRONZE', 'Bronze'), ('SILVER', 'Silver'), ('GOLD', 'Gold')], max_length=10)),
                ('reason', models.TextField(blank=True)),
                ('changed_at', models.DateTimeField(auto_now_add=True, db_index=True)),
                ('changed_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='status_changes_made', to=settings.AUTH_USER_MODEL)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='status_history', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'User Status History',
                'verbose_name_plural': 'User Status History',
                'db_table': 'users_status_history',
                'ordering': ['-changed_at'],
            },
        ),
        migrations.AddIndex(
            model_name='user',
            index=models.Index(fields=['tree_id', 'lft', 'rght'], name='users_user_tree_range_idx'),
        ),
        migrations.AddIndex(
            model_name='user',
            index=models.Index(fields=['level'], name='users_user_level_idx'),
        ),
        migrations.AddIndex(
            model_name='user',
            index=models.Index(fields=['status'], name='users_user_status_idx'),
        ),
        migrations.AddIndex(
            model_name='user',
            index=models.Index(fields=['-date_joined'], name='users_user_date_joined_idx'),
        ),
        migrations.AddIndex(
            model_name='user',
            index=models.Index(fields=['tree_id', 'lft'], name='users_user_tree_id_lft_idx'),
        ),
        migrations.AddConstraint(
            model_name='user',
            constraint=models.CheckConstraint(condition=models.Q(('personal_turnover__gte', 0)), name='users_personal_turnover_gte_0'),
        ),
        migrations.AddConstraint(
            model_name='user',
            constraint=models.CheckConstraint(condition=models.Q(('team_turnover__gte', 0)), name='users_team_turnover_gte_0'),
        ),
        migrations.AddConstraint(
            model_name='user',
            constraint=models.CheckConstraint(condition=models.Q(('bonus_balance__gte', 0)), name='users_bonus_balance_gte_0'),
        ),
        migrations.AddConstraint(
            model_name='user',
            constraint=models.CheckConstraint(condition=models.Q(('parent__isnull', True), models.Q(('parent', models.F('pk')), _negated=True), _connector='OR'), name='users_not_self_sponsored'),
        ),
        migrations.AddIndex(
            model_name='userstatushistory',
            index=models.Index(fields=['user', 'changed_at'], name='status_history_user_idx'),
        ),
    ]
