from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('demo_orders', '0008_product_is_recommended'),
        ('members', '0002_alter_member_options_alter_member_joined_at_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='Recommendation',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('items_json', models.TextField(default='[]', verbose_name='Recommended Product Names (JSON)')),
                ('generated_at', models.DateTimeField(auto_now=True, verbose_name='Last Generated')),
                ('member', models.OneToOneField(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='recommendation',
                    to='members.member',
                    verbose_name='Member',
                )),
            ],
            options={
                'verbose_name': 'AI Recommendation',
                'verbose_name_plural': 'AI Recommendations',
            },
        ),
    ]
