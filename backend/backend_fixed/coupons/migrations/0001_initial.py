from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('members', '0002_alter_member_options_alter_member_joined_at_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='Coupon',
            fields=[
                ('id',              models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name',            models.CharField(max_length=100, verbose_name='券名稱')),
                ('min_spend',       models.DecimalField(decimal_places=2, max_digits=8, verbose_name='最低消費門檻 (MOP)')),
                ('discount_amount', models.DecimalField(decimal_places=2, max_digits=8, verbose_name='折扣金額 (MOP)')),
                ('expire_date',     models.DateField(verbose_name='到期日')),
                ('is_used',         models.BooleanField(default=False, verbose_name='已使用')),
                ('created_at',      models.DateTimeField(auto_now_add=True, verbose_name='發放時間')),
                ('member',          models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='coupons',
                    to='members.member',
                    verbose_name='所屬會員',
                )),
            ],
            options={
                'verbose_name':        '優惠券',
                'verbose_name_plural': '優惠券',
                'ordering':            ['-created_at'],
            },
        ),
    ]
