# Generated manually for finance, campaigns, and church resources.

from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0003_userprofile_role_family_and_structure'),
        ('core', '0004_alter_tithe_options_tithe_recorded_by_tithe_status_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='ChurchAssetCategory',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=120)),
                ('description', models.TextField(blank=True)),
            ],
            options={
                'verbose_name': 'Church Asset Category',
                'verbose_name_plural': 'Church Asset Categories',
                'ordering': ['name'],
            },
        ),
        migrations.CreateModel(
            name='FundraisingCampaign',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=200)),
                ('description', models.TextField(blank=True)),
                ('target_amount', models.DecimalField(decimal_places=2, default=0, max_digits=12)),
                ('start_date', models.DateField()),
                ('end_date', models.DateField(blank=True, null=True)),
                ('is_active', models.BooleanField(default=True)),
            ],
            options={'ordering': ['-start_date', 'name']},
        ),
        migrations.CreateModel(
            name='OfferingCategory',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=120)),
                ('category_type', models.CharField(choices=[('zone', 'Zone Offering'), ('sunday', 'Sunday Offering'), ('friday', 'Friday Offering'), ('thanksgiving', 'Thanksgiving Offering'), ('children', 'Children Offering'), ('adults', 'Adults Offering'), ('special', 'Special Offering')], default='special', max_length=20)),
                ('description', models.TextField(blank=True)),
                ('is_active', models.BooleanField(default=True)),
            ],
            options={'ordering': ['name']},
        ),
        migrations.CreateModel(
            name='ChurchAsset',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=200)),
                ('serial_number', models.CharField(blank=True, max_length=120)),
                ('quantity', models.PositiveIntegerField(default=1)),
                ('condition', models.CharField(blank=True, max_length=120)),
                ('location', models.CharField(blank=True, max_length=200)),
                ('purchased_on', models.DateField(blank=True, null=True)),
                ('estimated_value', models.DecimalField(decimal_places=2, default=0, max_digits=12)),
                ('status', models.CharField(choices=[('active', 'Active'), ('maintenance', 'Under Maintenance'), ('retired', 'Retired')], default='active', max_length=20)),
                ('notes', models.TextField(blank=True)),
                ('category', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='assets', to='core.churchassetcategory')),
            ],
            options={'ordering': ['name']},
        ),
        migrations.CreateModel(
            name='FundraisingContribution',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('amount', models.DecimalField(decimal_places=2, max_digits=12)),
                ('contribution_date', models.DateField(default=django.utils.timezone.now)),
                ('week_label', models.CharField(blank=True, max_length=50)),
                ('notes', models.TextField(blank=True)),
                ('campaign', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='contributions', to='core.fundraisingcampaign')),
                ('contributor', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='fundraising_contributions', to='auth.user')),
                ('recorded_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='recorded_fundraising_contributions', to='auth.user')),
                ('zone', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='fundraising_contributions', to='accounts.zone')),
            ],
            options={'ordering': ['-contribution_date', '-id']},
        ),
        migrations.CreateModel(
            name='OfferingRecord',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('amount', models.DecimalField(decimal_places=2, max_digits=12)),
                ('week_label', models.CharField(blank=True, max_length=50)),
                ('month', models.PositiveSmallIntegerField()),
                ('year', models.PositiveIntegerField()),
                ('service_date', models.DateField(default=django.utils.timezone.now)),
                ('notes', models.TextField(blank=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('category', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='records', to='core.offeringcategory')),
                ('deacon_group', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='offering_records', to='accounts.deacongroup')),
                ('recorded_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='recorded_offerings', to='auth.user')),
                ('zone', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='offering_records', to='accounts.zone')),
            ],
            options={'ordering': ['-service_date', '-created_at']},
        ),
    ]
