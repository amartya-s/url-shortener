# Generated by Django 4.2.8 on 2023-12-29 09:13

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('url_shortener', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='urlshortener',
            name='long_url',
            field=models.CharField(max_length=50, unique=True),
        ),
        migrations.AlterField(
            model_name='urlshortener',
            name='short_url',
            field=models.CharField(max_length=5, unique=True),
        ),
    ]