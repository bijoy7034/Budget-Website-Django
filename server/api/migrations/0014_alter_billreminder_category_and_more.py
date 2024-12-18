# Generated by Django 5.1.2 on 2024-11-09 09:27

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0013_billreminder'),
    ]

    operations = [
        migrations.AlterField(
            model_name='billreminder',
            name='category',
            field=models.CharField(choices=[('Electricity', 'Electricity'), ('Water', 'Water'), ('Internet', 'Internet'), ('Subscription', 'Subscription'), ('Other', 'Other')], max_length=50),
        ),
        migrations.AlterField(
            model_name='billreminder',
            name='recurring_interval',
            field=models.CharField(choices=[('monthly', 'Monthly'), ('quarterly', 'Quarterly'), ('Weekly', 'Weekly'), ('yearly', 'Yearly'), ('one_time', 'One-Time')], default='monthly', max_length=20),
        ),
    ]
