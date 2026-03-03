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
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    phone = models.CharField(max_length=20, blank=True)
    church_branch = models.CharField(max_length=100, blank=True)
    zone = models.ForeignKey(Zone, on_delete=models.CASCADE, blank=True, null=True)
    ministry_role = models.ForeignKey(Ministry, on_delete=models.SET_NULL, blank=True, null=True)
    date_of_birth = models.DateField(blank=True, null=True)
    joined_at = models.DateField(auto_now_add=True)

    def age(self):
        today = date.today()
        return today.year - self.date_of_birth.year - ((today.month, today.day) < (self.date_of_birth.month, self.date_of_birth.day))
    def age_group(self):
        age = self.age()
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


