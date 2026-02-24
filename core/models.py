from django.db import models

# Create your models here.
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.urls import reverse
from django_resized import ResizedImageField
from ckeditor.fields import RichTextField
from ckeditor_uploader.fields import RichTextUploadingField
import uuid

class SiteConfig(models.Model):
    """Site configuration settings"""
    site_name = models.CharField(max_length=200, default="VCCT Mbezi Beach")
    site_logo = ResizedImageField(
        size=[200, 200],
        quality=85,
        upload_to='config/',
        blank=True,
        null=True,
        help_text="Logo size: 200x200 pixels"
    )
    site_favicon = ResizedImageField(
        size=[64, 64],
        quality=85,
        upload_to='config/',
        blank=True,
        null=True,
        help_text="Favicon size: 64x64 pixels"
    )
    hero_bg_image = ResizedImageField(
        size=[1920, 1080],
        quality=85,
        upload_to='config/',
        blank=True,
        null=True,
        help_text="Hero background size: 1920x1080 pixels"
    )
    
    # Contact Information
    contact_email = models.EmailField(default="info@tagkrt.or.tz")
    contact_phone = models.CharField(max_length=20, default="+255 784 344 079")
    address = models.TextField(default="Vijana street SIDO Road, Moshi Kilimanjaro")
    
    # Social Media
    facebook_url = models.URLField(blank=True, null=True)
    twitter_url = models.URLField(blank=True, null=True)
    instagram_url = models.URLField(blank=True, null=True)
    youtube_url = models.URLField(blank=True, null=True)
    whatsapp_number = models.CharField(max_length=20, blank=True, null=True)
    
    # About Information
    about_us = RichTextUploadingField(blank=True, null=True)
    mission = RichTextUploadingField(blank=True, null=True)
    vision = RichTextUploadingField(blank=True, null=True)
    
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Site Configuration"
        verbose_name_plural = "Site Configuration"
    
    def __str__(self):
        return self.site_name
    
    def save(self, *args, **kwargs):
        # Ensure only one instance exists
        if SiteConfig.objects.exists() and not self.pk:
            # Update existing instance
            existing = SiteConfig.objects.first()
            self.pk = existing.pk
        super().save(*args, **kwargs)

class HeroSlide(models.Model):
    """Hero slider slides"""
    title = models.CharField(max_length=200)
    subtitle = models.CharField(max_length=300)
    image = ResizedImageField(
        size=[1920, 1080],
        quality=85,
        upload_to='hero/',
        help_text="Recommended size: 1920x1080 pixels"
    )
    button1_text = models.CharField(max_length=50, default="Our Services")
    button1_link = models.CharField(max_length=200, default="#services")
    button2_text = models.CharField(max_length=50, default="Visit Us")
    button2_link = models.CharField(max_length=200, default="#visit")
    is_active = models.BooleanField(default=True)
    order = models.IntegerField(default=0)
    
    class Meta:
        ordering = ['order']
    
    def __str__(self):
        return self.title

class ServiceTime(models.Model):
    """Church service times"""
    SERVICE_TYPES = [
        ('children', 'Children Service'),
        ('teenagers', 'Teenagers Service'),
        ('english', 'English Service'),
        ('swahili', 'Swahili Service'),
        ('youth', 'Youth Service'),
        ('prayer', 'Prayer Meeting'),
        ('bible_study', 'Bible Study'),
        ('men', "Men's Fellowship"),
        ('women', "Women's Fellowship"),
    ]
    
    DAYS_OF_WEEK = [
        (0, 'Monday'),
        (1, 'Tuesday'),
        (2, 'Wednesday'),
        (3, 'Thursday'),
        (4, 'Friday'),
        (5, 'Saturday'),
        (6, 'Sunday'),
    ]
    
    title = models.CharField(max_length=200)
    service_type = models.CharField(max_length=20, choices=SERVICE_TYPES)
    day_of_week = models.IntegerField(choices=DAYS_OF_WEEK)
    start_time = models.TimeField()
    end_time = models.TimeField()
    location = models.CharField(max_length=200)
    description = models.TextField(blank=True, null=True)
    age_range = models.CharField(max_length=50, blank=True, null=True)
    icon = models.CharField(max_length=50, default="fas fa-church", 
                           help_text="Font Awesome icon class")
    image = ResizedImageField(
        size=[800, 600],
        quality=85,
        upload_to='services/',
        blank=True,
        null=True,
        help_text="Recommended size: 800x600 pixels"
    )
    is_active = models.BooleanField(default=True)
    order = models.IntegerField(default=0)
    
    class Meta:
        ordering = ['day_of_week', 'start_time', 'order']
        verbose_name = "Service Time"
        verbose_name_plural = "Service Times"
    
    def __str__(self):
        return f"{self.title} - {self.get_day_of_week_display()} {self.start_time}"
    
    def get_absolute_url(self):
        return reverse('services')

class Ministry(models.Model):
    """Church ministries"""
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('inactive', 'Inactive'),
        ('developing', 'Developing'),
    ]
    
    name = models.CharField(max_length=200)
    slug = models.SlugField(unique=True)
    tagline = models.CharField(max_length=300, blank=True, null=True)
    description = RichTextUploadingField()
    
    # Leadership
    leader = models.ForeignKey(User, on_delete=models.SET_NULL, 
                              null=True, blank=True, related_name='led_ministries')
    contact_email = models.EmailField(blank=True, null=True)
    contact_phone = models.CharField(max_length=20, blank=True, null=True)
    
    # Images
    logo = ResizedImageField(
        size=[400, 400],
        quality=85,
        upload_to='ministries/logos/',
        blank=True,
        null=True,
        help_text="Logo size: 400x400 pixels"
    )
    banner_image = ResizedImageField(
        size=[1200, 600],
        quality=85,
        upload_to='ministries/banners/',
        help_text="Banner size: 1200x600 pixels"
    )
    
    # Schedule
    meeting_days = models.CharField(max_length=100, blank=True, null=True)
    meeting_time = models.CharField(max_length=100, blank=True, null=True)
    meeting_location = models.CharField(max_length=200, blank=True, null=True)
    
    # Status
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    is_featured = models.BooleanField(default=False)
    order = models.IntegerField(default=0)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name_plural = "Ministries"
        ordering = ['order', 'name']
    
    def __str__(self):
        return self.name
    
    def get_absolute_url(self):
        return reverse('core:ministry_detail', kwargs={'slug': self.slug})
    
    @property
    def member_count(self):
        return self.members.filter(is_active=True).count()

class MinistryMember(models.Model):
    """Ministry membership"""
    ROLE_CHOICES = [
        ('leader', 'Leader'),
        ('assistant', 'Assistant Leader'),
        ('member', 'Member'),
        ('volunteer', 'Volunteer'),
    ]
    
    ministry = models.ForeignKey(Ministry, on_delete=models.CASCADE, related_name='members')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='ministry_memberships')
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='member')
    joined_date = models.DateField(default=timezone.now)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        unique_together = ['ministry', 'user']
    
    def __str__(self):
        return f"{self.user.get_full_name()} - {self.ministry.name}"

class EventCategory(models.Model):
    """Event categories"""
    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True)
    color = models.CharField(max_length=7, default='#3498db')
    icon = models.CharField(max_length=50, default="fas fa-calendar")
    
    class Meta:
        verbose_name_plural = "Event Categories"
    
    def __str__(self):
        return self.name

class Event(models.Model):
    """Church events"""
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('published', 'Published'),
        ('cancelled', 'Cancelled'),
        ('completed', 'Completed'),
    ]
    
    EVENT_TYPES = [
        ('service', 'Church Service'),
        ('prayer', 'Prayer Meeting'),
        ('fellowship', 'Fellowship'),
        ('conference', 'Conference'),
        ('outreach', 'Outreach'),
        ('training', 'Training'),
        ('special', 'Special Event'),
    ]
    
    # Basic Information
    title = models.CharField(max_length=200)
    slug = models.SlugField(unique=True)
    description = RichTextUploadingField()
    short_description = models.TextField(max_length=300)
    
    # Event Details
    event_type = models.CharField(max_length=20, choices=EVENT_TYPES, default='service')
    category = models.ForeignKey(EventCategory, on_delete=models.SET_NULL, null=True)
    
    # Date and Time
    start_date = models.DateField()
    start_time = models.TimeField()
    end_date = models.DateField()
    end_time = models.TimeField()
    is_recurring = models.BooleanField(default=False)
    
    # Location
    location = models.CharField(max_length=200)
    location_details = models.TextField(blank=True, null=True)
    online_link = models.URLField(blank=True, null=True)
    
    # Images
    featured_image = ResizedImageField(
        size=[1200, 800],
        quality=85,
        upload_to='events/',
        help_text="Featured image size: 1200x800 pixels"
    )
    
    # Registration
    requires_registration = models.BooleanField(default=False)
    max_attendees = models.PositiveIntegerField(default=0)
    registration_deadline = models.DateTimeField(blank=True, null=True)
    
    # Status
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    is_featured = models.BooleanField(default=False)
    
    # Metadata
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    published_at = models.DateTimeField(blank=True, null=True)
    
    class Meta:
        ordering = ['-start_date', '-start_time']
    
    def __str__(self):
        return self.title
    
    def get_absolute_url(self):
        return reverse('core:event_detail', kwargs={'slug': self.slug})
    
    @property
    def is_upcoming(self):
        return self.start_date >= timezone.now().date()
    
    @property
    def is_ongoing(self):
        now = timezone.now()
        start = timezone.make_aware(timezone.datetime.combine(self.start_date, self.start_time))
        end = timezone.make_aware(timezone.datetime.combine(self.end_date, self.end_time))
        return start <= now <= end

class EventRegistration(models.Model):
    """Event registrations"""
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('confirmed', 'Confirmed'),
        ('cancelled', 'Cancelled'),
        ('attended', 'Attended'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='registrations')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='event_registrations')
    
    # Personal Information
    full_name = models.CharField(max_length=200)
    email = models.EmailField()
    phone = models.CharField(max_length=20)
    
    # Status
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    registered_at = models.DateTimeField(auto_now_add=True)
    confirmed_at = models.DateTimeField(blank=True, null=True)
    
    class Meta:
        unique_together = ['event', 'email']
    
    def __str__(self):
        return f"{self.full_name} - {self.event.title}"

class BibleVerse(models.Model):
    """Daily Bible verses"""
    verse = models.TextField()
    reference = models.CharField(max_length=100)
    display_date = models.DateField(default=timezone.now)
    display_on_homepage = models.BooleanField(default=False)
    
    class Meta:
        ordering = ['-display_date']
    
    def __str__(self):
        return self.reference

class ContactMessage(models.Model):
    """Contact form messages"""
    STATUS_CHOICES = [
        ('new', 'New'),
        ('read', 'Read'),
        ('replied', 'Replied'),
        ('archived', 'Archived'),
    ]
    
    name = models.CharField(max_length=200)
    email = models.EmailField()
    phone = models.CharField(max_length=20, blank=True, null=True)
    subject = models.CharField(max_length=200)
    message = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='new')
    created_at = models.DateTimeField(auto_now_add=True)
    replied_at = models.DateTimeField(blank=True, null=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.name}: {self.subject}"

class GalleryImage(models.Model):
    """Image gallery"""
    title = models.CharField(max_length=200)
    image = ResizedImageField(
        size=[1200, 800],
        quality=85,
        upload_to='gallery/',
        help_text="Image size: 1200x800 pixels"
    )
    description = models.TextField(blank=True, null=True)
    category = models.CharField(max_length=100, blank=True, null=True)
    is_featured = models.BooleanField(default=False)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-uploaded_at']
    
    def __str__(self):
        return self.title

class Testimonial(models.Model):
    """Member testimonials"""
    author = models.CharField(max_length=200)
    role = models.CharField(max_length=100, blank=True, null=True)
    content = models.TextField()
    image = ResizedImageField(
        size=[400, 400],
        quality=85,
        upload_to='testimonials/',
        blank=True,
        null=True,
        help_text="Profile image size: 400x400 pixels"
    )
    is_active = models.BooleanField(default=True)
    order = models.IntegerField(default=0)
    
    class Meta:
        ordering = ['order']
    
    def __str__(self):
        return self.author
    
class Tithe(models.Model):
    """Tithe records"""

    PAYMENT_METHODS = [
        ('cash', 'Cash'),
        ('mpesa', 'M-Pesa'),
        ('bank', 'Bank'),
        ('other', 'Other'),
    ]
    
    STATUS_CHOICES = [
        ('paid', 'Paid'),
        ('pending', 'Pending'),
        ('cancelled', 'Cancelled'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='tithes')
    amount = models.DecimalField(max_digits=12, decimal_places=2)

    # muhimu kwa statistics
    month = models.PositiveSmallIntegerField()  # 1–12
    year = models.PositiveIntegerField()

    payment_method = models.CharField(
        max_length=20, choices=PAYMENT_METHODS, default='cash'
    )
    
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default='paid'
    )

    reference = models.CharField(max_length=100, blank=True, null=True)
    notes = models.TextField(blank=True, null=True)

    date_paid = models.DateTimeField(default=timezone.now)
    
    # Add recorded_by field
    recorded_by = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='recorded_tithes'
    )

    class Meta:
        ordering = ['-year', '-month', '-date_paid']
        unique_together = ('user', 'month', 'year')  # mtu asilipa mara 2 kwa mwezi huohuo
        indexes = [
            models.Index(fields=['year', 'month']),
            models.Index(fields=['user']),
            models.Index(fields=['status']),
            models.Index(fields=['date_paid']),
        ]

    def __str__(self):
        return f"{self.user.get_full_name()} - {self.amount} ({self.month}/{self.year})"

    @property
    def period(self):
        return f"{self.month}/{self.year}"
        
    @property
    def get_month_display(self):
        """Return month name"""
        months = {
            1: 'January', 2: 'February', 3: 'March', 4: 'April',
            5: 'May', 6: 'June', 7: 'July', 8: 'August',
            9: 'September', 10: 'October', 11: 'November', 12: 'December'
        }
        return months.get(self.month, '')