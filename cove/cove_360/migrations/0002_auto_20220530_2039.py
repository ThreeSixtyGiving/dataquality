# Generated by Django 2.2.27 on 2022-05-30 20:39

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('cove_360', '0001_initial'),
    ]

    operations = [
        migrations.RenameField(
            model_name='supplieddatastatus',
            old_name='publisher',
            new_name='_publisher',
        ),
    ]
