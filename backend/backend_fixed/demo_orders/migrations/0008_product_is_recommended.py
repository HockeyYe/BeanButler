from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('demo_orders', '0007_five_statuses'),
    ]

    operations = [
        migrations.AddField(
            model_name='product',
            name='is_recommended',
            field=models.BooleanField(default=False, verbose_name='Show in Recommended'),
        ),
    ]
