# Generated manually for deacon group member assignment.

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0003_userprofile_role_family_and_structure'),
    ]

    operations = [
        migrations.AddField(
            model_name='userprofile',
            name='deacon_group',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='members', to='accounts.deacongroup'),
        ),
    ]
