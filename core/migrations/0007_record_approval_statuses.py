from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0006_actionapprovallog'),
    ]

    operations = [
        migrations.AddField(
            model_name='churchasset',
            name='approval_status',
            field=models.CharField(choices=[('pending', 'Pending Approval'), ('approved', 'Approved'), ('rejected', 'Rejected'), ('auto_approved', 'Auto Approved')], default='auto_approved', max_length=20),
        ),
        migrations.AddField(
            model_name='fundraisingcontribution',
            name='approval_status',
            field=models.CharField(choices=[('pending', 'Pending Approval'), ('approved', 'Approved'), ('rejected', 'Rejected'), ('auto_approved', 'Auto Approved')], default='auto_approved', max_length=20),
        ),
        migrations.AddField(
            model_name='offeringrecord',
            name='approval_status',
            field=models.CharField(choices=[('pending', 'Pending Approval'), ('approved', 'Approved'), ('rejected', 'Rejected'), ('auto_approved', 'Auto Approved')], default='auto_approved', max_length=20),
        ),
        migrations.AddField(
            model_name='tithe',
            name='approval_status',
            field=models.CharField(choices=[('pending', 'Pending Approval'), ('approved', 'Approved'), ('rejected', 'Rejected'), ('auto_approved', 'Auto Approved')], default='auto_approved', max_length=20),
        ),
    ]
