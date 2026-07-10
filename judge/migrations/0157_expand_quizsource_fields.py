# Generated manually to expand QuizSource with admin management fields

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('judge', '0156_siteconfiguration_quiz_enabled'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='quizsource',
            options={'verbose_name': 'quiz source / exam', 'verbose_name_plural': 'quiz sources / exams'},
        ),
        migrations.AddField(
            model_name='quizsource',
            name='is_visible',
            field=models.BooleanField(default=True, help_text='Whether this exam appears in the exam list.', verbose_name='visible to users'),
        ),
        migrations.AddField(
            model_name='quizsource',
            name='require_login',
            field=models.BooleanField(default=False, help_text='Users must be logged in to view and start this exam.', verbose_name='require login'),
        ),
        migrations.AddField(
            model_name='quizsource',
            name='is_locked',
            field=models.BooleanField(default=False, help_text='Exam is locked and cannot be started by users.', verbose_name='locked'),
        ),
        migrations.AddField(
            model_name='quizsource',
            name='is_featured',
            field=models.BooleanField(default=False, help_text='Show as featured exam.', verbose_name='featured'),
        ),
        migrations.AddField(
            model_name='quizsource',
            name='is_organization_only',
            field=models.BooleanField(default=False, help_text='Only members of selected organizations can view and start this exam.', verbose_name='organization only'),
        ),
        migrations.AddField(
            model_name='quizsource',
            name='organizations',
            field=models.ManyToManyField(blank=True, help_text='Organizations that can access this exam (empty = all if unchecked).', to='judge.organization', verbose_name='organizations'),
        ),
        migrations.AddField(
            model_name='quizsource',
            name='description',
            field=models.TextField(blank=True, default='', verbose_name='description'),
        ),
        migrations.AddField(
            model_name='quizsource',
            name='default_duration',
            field=models.IntegerField(default=45, verbose_name='default duration (minutes)'),
        ),
        migrations.AddField(
            model_name='quizsource',
            name='created_by',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL, verbose_name='created by'),
        ),
        migrations.AddField(
            model_name='quizsource',
            name='created_at',
            field=models.DateTimeField(auto_now_add=True, default='2026-01-01', verbose_name='created at'),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='quizsource',
            name='updated_at',
            field=models.DateTimeField(auto_now=True, verbose_name='updated at'),
        ),
    ]
