from django.db import models
from django.contrib.auth.models import User
from datetime import date
from core.models import Ministry

class Zone(models.Model):
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name
    
class ChurchBranch(models.Model):
    name = models.CharField(max_length=100)
    zone = models.ForeignKey(Zone, on_delete=models.CASCADE)

    def __str__(self):
        return self.name  
          
class UserProfile(models.Model):
    ROLE_CHOICES = [
        ('member', 'Church Member'),
        ('pastor', 'Pastor'),
        ('assistant_pastor', 'Assistant Pastor'),
        ('elder_council', 'Baraza la Wazee'),
        ('institution_manager', 'Institution Management'),
        ('secretary', 'Church Secretary'),
        ('accountant', 'Church Accountant'),
        ('zone_leader', 'Zone Leader'),
        ('deacon_leader', 'Deacon Leader'),
    ]

    MARITAL_STATUS_CHOICES = [
        ('single', 'Single'),
        ('married', 'Married'),
        ('widowed', 'Widowed'),
        ('divorced', 'Divorced'),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE)
    role = models.CharField(max_length=30, choices=ROLE_CHOICES, default='member')
    phone = models.CharField(max_length=20, blank=True)
    church_branch = models.CharField(max_length=100, blank=True)
    zone = models.ForeignKey(Zone, on_delete=models.CASCADE, blank=True, null=True)
    deacon_group = models.ForeignKey('DeaconGroup', on_delete=models.SET_NULL, blank=True, null=True, related_name='members')
    ministry_role = models.ForeignKey(Ministry, on_delete=models.SET_NULL, blank=True, null=True)
    marital_status = models.CharField(max_length=20, choices=MARITAL_STATUS_CHOICES, blank=True)
    spouse_name = models.CharField(max_length=150, blank=True)
    occupation = models.CharField(max_length=150, blank=True)
    tithe_card_number = models.CharField(max_length=50, blank=True, unique=True, null=True)
    date_of_birth = models.DateField(blank=True, null=True)
    joined_at = models.DateField(auto_now_add=True)

    @property
    def is_management_role(self):
        return self.role in {'pastor', 'assistant_pastor', 'elder_council', 'institution_manager'}

    @property
    def is_finance_role(self):
        return self.role in {'secretary', 'accountant'}

    @property
    def can_manage_full_system(self):
        return self.role in {'pastor', 'secretary'}

    def age(self):
        if not self.date_of_birth:
            return None
        today = date.today()
        return today.year - self.date_of_birth.year - ((today.month, today.day) < (self.date_of_birth.month, self.date_of_birth.day))
    def age_group(self):
        age = self.age()
        if age is None:
            return "Unknown"
        if age < 13:
            return "Child"
        elif age < 20:
            return "Teenager"
        elif age < 35:
            return "Young Adult"
        elif age < 50:
            return "Adult"
        else:
            return "Senior"

    def __str__(self):
        return self.user.username
    
# accounts/models.py
class ChurchLeader(models.Model):
    LEVEL_CHOICES = (
        (1, "Founder / Baba wa Kiroho"),
        (2, "Askofu / Senior Pastor"),
        (3, "Mchungaji"),
        (4, "Mzee wa Kanisa"),
        (5, "Kiongozi wa Huduma"),
    )

    full_name = models.CharField(max_length=200)
    title = models.CharField(max_length=100)
    level = models.PositiveIntegerField(choices=LEVEL_CHOICES)
    photo = models.ImageField(upload_to='leaders/')
    vision_message = models.TextField(blank=True, null=True)
    biography = models.TextField(blank=True, null=True)
    is_active = models.BooleanField(default=True)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['level', 'order']

    def __str__(self):
        return f"{self.full_name} - {self.title}"


class ZoneLeadership(models.Model):
    ROLE_CHOICES = [
        ('zone_leader', 'Zone Leader'),
        ('assistant_zone_leader', 'Assistant Zone Leader'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='zone_leaderships')
    zone = models.ForeignKey(Zone, on_delete=models.CASCADE, related_name='leaders')
    role = models.CharField(max_length=30, choices=ROLE_CHOICES, default='zone_leader')
    appointed_on = models.DateField(auto_now_add=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        unique_together = ('user', 'zone', 'role')

    def __str__(self):
        return f"{self.user.get_full_name() or self.user.username} - {self.zone.name}"


class DeaconGroup(models.Model):
    name = models.CharField(max_length=120)
    zone = models.ForeignKey(Zone, on_delete=models.CASCADE, related_name='deacon_groups')
    description = models.TextField(blank=True)
    leader = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='leading_deacon_groups',
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['zone__name', 'name']

    def __str__(self):
        return f"{self.name} ({self.zone.name})"


class FamilyMember(models.Model):
    RELATIONSHIP_CHOICES = [
        ('spouse', 'Spouse'),
        ('child', 'Child'),
        ('parent', 'Parent'),
        ('sibling', 'Sibling'),
        ('other', 'Other'),
    ]

    primary_member = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name='family_members')
    full_name = models.CharField(max_length=200)
    relationship = models.CharField(max_length=20, choices=RELATIONSHIP_CHOICES)
    gender = models.CharField(max_length=20, blank=True)
    date_of_birth = models.DateField(blank=True, null=True)
    phone = models.CharField(max_length=20, blank=True)
    is_member_account = models.BooleanField(default=False)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['full_name']

    def __str__(self):
        return f"{self.full_name} - {self.primary_member.user.username}"


