# -*- coding: utf-8 -*-
# Generated by Django 1.11.5 on 2017-10-02 18:03
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('actionslog', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='logaction',
            name='action',
            field=models.PositiveSmallIntegerField(blank=True, choices=[(100, 'create'), (110, 'success'), (130, 'activate'), (150, 'authorize'), (180, 'view'), (200, 'update'), (250, 'suspend'), (260, 'unsuspend'), (300, 'delete'), (500, 'terminate'), (999, 'failed'), (1000, 'error')], null=True, verbose_name='action'),
        ),
        migrations.AlterField(
            model_name='logaction',
            name='created_at',
            field=models.DateTimeField(auto_now_add=True, db_index=True, verbose_name='created at'),
        ),
    ]