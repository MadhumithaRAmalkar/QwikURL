# Generated by Django 5.2 on 2025-05-06 16:49

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('shortner', '0003_alter_url_options_url_created_at_alter_url_link'),
    ]

    operations = [
        migrations.AddField(
            model_name='url',
            name='last_clicked',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name='url',
            name='created_at',
            field=models.DateTimeField(auto_now_add=True),
        ),
    ]
