# Generated by Django 5.0 on 2024-01-05 06:31

import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0002_simulation_status"),
    ]

    operations = [
        migrations.AddField(
            model_name="simulation",
            name="created_at",
            field=models.DateTimeField(
                auto_now_add=True, default=django.utils.timezone.now, verbose_name="Data de criação"
            ),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="simulation",
            name="modified_at",
            field=models.DateTimeField(auto_now=True, verbose_name="Data de modificação"),
        ),
        migrations.AlterField(
            model_name="simulation",
            name="status",
            field=models.CharField(
                choices=[
                    ("I", "Simulação pronta para execução"),
                    ("R", "Rodando"),
                    ("S", "Simulação executada"),
                    ("F", "Simulação Falhou"),
                ],
                default="I",
                max_length=1,
                verbose_name="Status",
            ),
        ),
    ]
