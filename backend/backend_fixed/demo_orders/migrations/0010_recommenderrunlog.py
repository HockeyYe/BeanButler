from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('demo_orders', '0009_recommendation'),
    ]

    operations = [
        migrations.CreateModel(
            name='RecommenderRunLog',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('ran_at', models.DateTimeField(auto_now_add=True, verbose_name='Run Time')),
                ('triggered_by', models.CharField(
                    choices=[('manual', 'Manual (Admin Button)'), ('scheduled', 'Scheduled (Cron)')],
                    default='manual', max_length=20, verbose_name='Trigger',
                )),
                ('members_updated', models.PositiveIntegerField(default=0, verbose_name='Members Updated')),
                ('members_created', models.PositiveIntegerField(default=0, verbose_name='New Entries Created')),
                ('duration_secs', models.FloatField(default=0.0, verbose_name='Duration (s)')),
                ('note', models.TextField(blank=True, verbose_name='Notes / Errors')),
            ],
            options={
                'verbose_name': 'Recommender Run Log',
                'verbose_name_plural': 'Recommender Run Logs',
                'ordering': ['-ran_at'],
            },
        ),
    ]
