                                               

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('reservations', '0001_initial'),
    ]

    operations = [
        migrations.RemoveConstraint(
            model_name='reservation',
            name='resv_max_ext',
        ),
        migrations.RemoveField(
            model_name='reservation',
            name='extension_count',
        ),
    ]
