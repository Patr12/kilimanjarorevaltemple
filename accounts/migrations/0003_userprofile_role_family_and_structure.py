# Generated manually for expanded church roles and family structure.

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0004_alter_tithe_options_tithe_recorded_by_tithe_status_and_more'),
        ('accounts', '0002_zone_userprofile_date_of_birth_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='userprofile',
            name='marital_status',
            field=models.CharField(blank=True, choices=[('single', 'Single'), ('married', 'Married'), ('widowed', 'Widowed'), ('divorced', 'Divorced')], max_length=20),
        ),
        migrations.AddField(
            model_name='userprofile',
            name='occupation',
            field=models.CharField(blank=True, max_length=150),
        ),
        migrations.AddField(
            model_name='userprofile',
            name='role',
            field=models.CharField(choices=[('member', 'Church Member'), ('pastor', 'Pastor'), ('assistant_pastor', 'Assistant Pastor'), ('elder_council', 'Baraza la Wazee'), ('institution_manager', 'Institution Management'), ('secretary', 'Church Secretary'), ('accountant', 'Church Accountant'), ('zone_leader', 'Zone Leader'), ('deacon_leader', 'Deacon Leader')], default='member', max_length=30),
        ),
        migrations.AddField(
            model_name='userprofile',
            name='spouse_name',
            field=models.CharField(blank=True, max_length=150),
        ),
        migrations.AddField(
            model_name='userprofile',
            name='tithe_card_number',
            field=models.CharField(blank=True, max_length=50, null=True, unique=True),
        ),
        migrations.CreateModel(
            name='DeaconGroup',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=120)),
                ('description', models.TextField(blank=True)),
                ('is_active', models.BooleanField(default=True)),
                ('leader', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='leading_deacon_groups', to='auth.user')),
                ('zone', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='deacon_groups', to='accounts.zone')),
            ],
            options={'ordering': ['zone__name', 'name']},
        ),
        migrations.CreateModel(
            name='FamilyMember',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('full_name', models.CharField(max_length=200)),
                ('relationship', models.CharField(choices=[('spouse', 'Spouse'), ('child', 'Child'), ('parent', 'Parent'), ('sibling', 'Sibling'), ('other', 'Other')], max_length=20)),
                ('gender', models.CharField(blank=True, max_length=20)),
                ('date_of_birth', models.DateField(blank=True, null=True)),
                ('phone', models.CharField(blank=True, max_length=20)),
                ('is_member_account', models.BooleanField(default=False)),
                ('notes', models.TextField(blank=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('primary_member', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='family_members', to='accounts.userprofile')),
            ],
            options={'ordering': ['full_name']},
        ),
        migrations.CreateModel(
            name='ZoneLeadership',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('role', models.CharField(choices=[('zone_leader', 'Zone Leader'), ('assistant_zone_leader', 'Assistant Zone Leader')], default='zone_leader', max_length=30)),
                ('appointed_on', models.DateField(auto_now_add=True)),
                ('is_active', models.BooleanField(default=True)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='zone_leaderships', to='auth.user')),
                ('zone', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='leaders', to='accounts.zone')),
            ],
            options={'unique_together': {('user', 'zone', 'role')}},
        ),
    ]
