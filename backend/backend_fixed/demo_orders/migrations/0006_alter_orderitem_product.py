from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('demo_orders', '0005_alter_material_expiry_date_alter_material_quantity_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='orderitem',
            name='product',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                to='demo_orders.product',
                verbose_name='Product Name',
            ),
        ),
    ]
