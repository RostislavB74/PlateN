# Generated by Django 5.0.4 on 2024-04-13 11:59

from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Photo',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('photo', models.BinaryField(null=True)),
                ('timestamp', models.DateTimeField(auto_now=True)),
                ('type', models.IntegerField(null=True)),
                ('accuracy', models.FloatField(null=True)),
                ('recognized_car_number', models.CharField(max_length=16, null=True)),
            ],
        ),
    ]
