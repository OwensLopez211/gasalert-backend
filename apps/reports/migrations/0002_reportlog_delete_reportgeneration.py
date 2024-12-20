# Generated by Django 5.0.1 on 2024-12-10 03:09

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("reports", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="ReportLog",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("report_type", models.CharField(max_length=50)),
                ("date_range", models.CharField(max_length=50)),
                ("generated_at", models.DateTimeField(auto_now_add=True)),
                ("success", models.BooleanField(default=True)),
                ("error_message", models.TextField(blank=True, null=True)),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="report_logs",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "ordering": ["-generated_at"],
            },
        ),
        migrations.DeleteModel(
            name="ReportGeneration",
        ),
    ]
