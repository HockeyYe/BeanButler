from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('demo_orders', '0006_alter_orderitem_product'),
    ]

    operations = [
        # 1. 把舊 DONE 資料先改成 PICKED_UP
        migrations.RunSQL(
            sql="UPDATE demo_orders_order SET status = 'PICKED_UP' WHERE status = 'DONE';",
            reverse_sql="UPDATE demo_orders_order SET status = 'DONE' WHERE status = 'PICKED_UP';"
        ),
        # 2. 更新 field choices（Django 不會真正約束 SQLite，但 choices 要同步）
        migrations.AlterField(
            model_name='order',
            name='status',
            field=models.CharField(
                max_length=20,
                default='PENDING',
                verbose_name='Order Status',
                choices=[
                    ('PENDING',     '待確認'),
                    ('CONFIRMED',   '已確認'),
                    ('IN_PROGRESS', '製作中'),
                    ('READY',       '待取餐'),
                    ('PICKED_UP',   '已取餐'),
                ],
            ),
        ),
    ]
