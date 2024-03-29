# Generated by Django 2.2.27 on 2022-05-30 19:33

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('input', '0008_supplieddata_data_schema_version'),
    ]

    operations = [
        migrations.CreateModel(
            name='SuppliedDataStatus',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('passed', models.BooleanField(default=False)),
                ('publisher', models.TextField(blank=True, null=True)),
                ('supplied_data', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='input.SuppliedData')),
            ],
        ),
    ]
