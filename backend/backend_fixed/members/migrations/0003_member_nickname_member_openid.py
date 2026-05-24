from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('members', '0002_alter_member_options_alter_member_joined_at_and_more'),
    ]

    operations = [
        migrations.RenameField(
            model_name='member',
            old_name='name',
            new_name='name',   # kept — we only ADD new columns
        ),
        migrations.AlterField(
            model_name='member',
            name='name',
            field=models.CharField(max_length=50, verbose_name='Real Name'),
        ),
        migrations.AddField(
            model_name='member',
            name='nickname',
            field=models.CharField(blank=True, max_length=50, verbose_name='Nickname / Display Name'),
        ),
        migrations.AddField(
            model_name='member',
            name='openid',
            field=models.CharField(blank=True, max_length=100, null=True, unique=True, verbose_name='WeChat OpenID'),
        ),
    ]
