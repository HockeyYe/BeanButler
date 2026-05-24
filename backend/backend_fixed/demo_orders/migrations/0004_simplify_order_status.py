from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('demo_orders', '0003_alter_material_options_alter_order_options_and_more'),
    ]

    operations = [
        # 先把已有的 ACCEPTED / MAKING 訂單改為 PENDING，避免 status 值不合法
        migrations.RunSQL(
            "UPDATE demo_orders_order SET status='PENDING' WHERE status IN ('ACCEPTED','MAKING');",
            reverse_sql=migrations.RunSQL.noop,
        ),
        # 再修改 status 欄位的 choices
        migrations.AlterField(
            model_name='order',
            name='status',
            field=models.CharField(
                max_length=20,
                choices=[
                    ('PENDING', '製作中'),
                    ('READY',   '待取餐'),
                    ('DONE',    '已完成'),
                ],
                default='PENDING',
                verbose_name='Order Status',
            ),
        ),
    ]
