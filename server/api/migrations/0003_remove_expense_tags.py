# Generated by Django 5.1.2 on 2024-11-02 07:15

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0002_alter_incomesource_user_category_expense_income'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='expense',
            name='tags',
        ),
    ]