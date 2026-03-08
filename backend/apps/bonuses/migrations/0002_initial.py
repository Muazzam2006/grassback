                                               

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('bonuses', '0001_initial'),
        ('orders', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name='bonus',
            name='order',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='bonuses', to='orders.order'),
        ),
        migrations.AddField(
            model_name='bonus',
            name='source_user',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='bonuses_generated', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='bonus',
            name='user',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='bonuses_received', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddIndex(
            model_name='mlmrule',
            index=models.Index(fields=['agent_status', 'level'], name='mlm_rule_status_level_idx'),
        ),
        migrations.AddIndex(
            model_name='mlmrule',
            index=models.Index(fields=['is_active'], name='mlm_rule_is_active_idx'),
        ),
        migrations.AddConstraint(
            model_name='mlmrule',
            constraint=models.UniqueConstraint(condition=models.Q(('is_active', True)), fields=('agent_status', 'level'), name='unique_active_mlm_rule_status_level'),
        ),
        migrations.AddConstraint(
            model_name='mlmrule',
            constraint=models.CheckConstraint(condition=models.Q(('value__gte', 0)), name='mlm_rule_value_gte_0'),
        ),
        migrations.AddConstraint(
            model_name='mlmrule',
            constraint=models.CheckConstraint(condition=models.Q(('level__gt', 0)), name='mlm_rule_level_gt_0'),
        ),
        migrations.AddIndex(
            model_name='bonus',
            index=models.Index(fields=['user'], name='bonus_user_idx'),
        ),
        migrations.AddIndex(
            model_name='bonus',
            index=models.Index(fields=['order'], name='bonus_order_idx'),
        ),
        migrations.AddIndex(
            model_name='bonus',
            index=models.Index(fields=['status'], name='bonus_status_idx'),
        ),
        migrations.AddIndex(
            model_name='bonus',
            index=models.Index(fields=['created_at'], name='bonus_created_at_idx'),
        ),
        migrations.AddConstraint(
            model_name='bonus',
            constraint=models.UniqueConstraint(fields=('user', 'order', 'level', 'bonus_type'), name='uniq_bonus_user_order_lvl_tp'),
        ),
        migrations.AddConstraint(
            model_name='bonus',
            constraint=models.CheckConstraint(condition=models.Q(('amount__gt', 0)), name='bonus_amount_gt_0'),
        ),
        migrations.AddConstraint(
            model_name='bonus',
            constraint=models.CheckConstraint(condition=models.Q(('user', models.F('source_user')), _negated=True), name='bonus_user_not_source_user'),
        ),
        migrations.AddConstraint(
            model_name='bonus',
            constraint=models.CheckConstraint(condition=models.Q(('level__gt', 0)), name='bonus_level_gt_0'),
        ),
    ]
