# Generated by Django 5.1.7 on 2025-06-09 09:02

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0012_wishlist'),
    ]

    operations = [
        migrations.AddField(
            model_name='order',
            name='cancel_reson',
            field=models.CharField(blank=True, max_length=500),
        ),
    ]
