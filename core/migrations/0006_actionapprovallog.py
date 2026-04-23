from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0005_finance_resources_and_offerings'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='ActionApprovalLog',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('action_area', models.CharField(choices=[('roles', 'Role Management'), ('assets', 'Church Assets'), ('offerings', 'Offerings'), ('tithes', 'Tithes')], max_length=20)),
                ('action_type', models.CharField(choices=[('create', 'Create'), ('update', 'Update'), ('delete', 'Delete'), ('approve', 'Approve'), ('reject', 'Reject')], max_length=20)),
                ('entity_type', models.CharField(max_length=50)),
                ('entity_id', models.CharField(blank=True, max_length=50)),
                ('entity_label', models.CharField(max_length=200)),
                ('description', models.TextField(blank=True)),
                ('previous_data', models.JSONField(blank=True, default=dict)),
                ('new_data', models.JSONField(blank=True, default=dict)),
                ('approval_status', models.CharField(choices=[('pending', 'Pending'), ('approved', 'Approved'), ('rejected', 'Rejected'), ('auto_approved', 'Auto Approved')], default='pending', max_length=20)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('approved_at', models.DateTimeField(blank=True, null=True)),
                ('approved_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='approved_action_logs', to=settings.AUTH_USER_MODEL)),
                ('performed_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='performed_action_logs', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
    ]
