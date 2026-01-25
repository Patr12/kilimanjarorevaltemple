from django.contrib import admin

# Register your models here.
from django.contrib import admin
from .models import (
    SiteConfig, HeroSlide, ServiceTime, Ministry, MinistryMember,
    EventCategory, Event, EventRegistration,
    BibleVerse, ContactMessage, GalleryImage, Testimonial
)

# ------------------------------
# SiteConfig
# ------------------------------
@admin.register(SiteConfig)
class SiteConfigAdmin(admin.ModelAdmin):
    list_display = ('site_name', 'contact_email', 'contact_phone', 'updated_at')
    search_fields = ('site_name', 'contact_email', 'contact_phone')
    readonly_fields = ('updated_at',)

# ------------------------------
# HeroSlide
# ------------------------------
@admin.register(HeroSlide)
class HeroSlideAdmin(admin.ModelAdmin):
    list_display = ('title', 'is_active', 'order')
    list_editable = ('is_active', 'order')
    search_fields = ('title', 'subtitle')
    list_filter = ('is_active',)

# ------------------------------
# ServiceTime
# ------------------------------
@admin.register(ServiceTime)
class ServiceTimeAdmin(admin.ModelAdmin):
    list_display = ('title', 'service_type', 'day_of_week', 'start_time', 'end_time', 'is_active')
    list_filter = ('service_type', 'day_of_week', 'is_active')
    search_fields = ('title', 'location')
    ordering = ('day_of_week', 'start_time')

# ------------------------------
# MinistryMember Inline
# ------------------------------
class MinistryMemberInline(admin.TabularInline):
    model = MinistryMember
    extra = 1
    fields = ('user', 'role', 'joined_date', 'is_active')
    readonly_fields = ()
    autocomplete_fields = ['user']

# ------------------------------
# Ministry
# ------------------------------
@admin.register(Ministry)
class MinistryAdmin(admin.ModelAdmin):
    list_display = ('name', 'leader', 'status', 'is_featured', 'order')
    search_fields = ('name', 'tagline', 'leader__username')
    list_filter = ('status', 'is_featured')
    ordering = ('order', 'name')
    inlines = [MinistryMemberInline]
    prepopulated_fields = {"slug": ("name",)}

# ------------------------------
# EventCategory
# ------------------------------
@admin.register(EventCategory)
class EventCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'color', 'icon')
    search_fields = ('name', 'slug')
    prepopulated_fields = {"slug": ("name",)}

# ------------------------------
# Event
# ------------------------------
@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = ('title', 'event_type', 'category', 'start_date', 'start_time', 'status', 'is_featured')
    list_filter = ('event_type', 'category', 'status', 'is_featured')
    search_fields = ('title', 'slug', 'location')
    prepopulated_fields = {"slug": ("title",)}
    date_hierarchy = 'start_date'
    ordering = ('-start_date', '-start_time')

# ------------------------------
# EventRegistration
# ------------------------------
@admin.register(EventRegistration)
class EventRegistrationAdmin(admin.ModelAdmin):
    list_display = ('full_name', 'email', 'event', 'status', 'registered_at', 'confirmed_at')
    list_filter = ('status', 'event')
    search_fields = ('full_name', 'email', 'phone', 'event__title')
    readonly_fields = ('registered_at', 'confirmed_at')

# ------------------------------
# BibleVerse
# ------------------------------
@admin.register(BibleVerse)
class BibleVerseAdmin(admin.ModelAdmin):
    list_display = ('reference', 'display_date', 'display_on_homepage')
    list_filter = ('display_on_homepage',)
    search_fields = ('verse', 'reference')
    ordering = ('-display_date',)

# ------------------------------
# ContactMessage
# ------------------------------
@admin.register(ContactMessage)
class ContactMessageAdmin(admin.ModelAdmin):
    list_display = ('name', 'email', 'subject', 'status', 'created_at')
    list_filter = ('status',)
    search_fields = ('name', 'email', 'subject', 'message')
    readonly_fields = ('created_at', 'replied_at')
    ordering = ('-created_at',)

# ------------------------------
# GalleryImage
# ------------------------------
@admin.register(GalleryImage)
class GalleryImageAdmin(admin.ModelAdmin):
    list_display = ('title', 'category', 'is_featured', 'uploaded_at')
    list_filter = ('is_featured', 'category')
    search_fields = ('title', 'category')
    ordering = ('-uploaded_at',)

# ------------------------------
# Testimonial
# ------------------------------
@admin.register(Testimonial)
class TestimonialAdmin(admin.ModelAdmin):
    list_display = ('author', 'role', 'is_active', 'order')
    list_filter = ('is_active',)
    search_fields = ('author', 'role', 'content')
    ordering = ('order',)
