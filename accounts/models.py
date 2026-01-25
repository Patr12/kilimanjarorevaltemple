from django.db import models
from django.contrib.auth.models import User
# Create your models here.

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    phone = models.CharField(max_length=20, blank=True)
    church_branch = models.CharField(max_length=100, blank=True)
    joined_at = models.DateField(auto_now_add=True)

    def __str__(self):
        return self.user.username
# core/models.py
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


