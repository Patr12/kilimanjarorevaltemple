from django.contrib import admin

# Register your models here.
from django.contrib import admin
from .models import (
    SiteConfig, HeroSlide, ServiceTime, Ministry, MinistryMember,
    EventCategory, Event, EventRegistration,
    BibleVerse, ContactMessage, GalleryImage, Testimonial, Tithe,
    OfferingCategory, OfferingRecord, FundraisingCampaign, FundraisingContribution,
    ChurchAssetCategory, ChurchAsset, ActionApprovalLog
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


@admin.register(Tithe)
class TitheAdmin(admin.ModelAdmin):
    list_display = ('user', 'amount', 'month', 'year', 'status', 'approval_status', 'payment_method', 'recorded_by', 'date_paid')
    list_filter = ('status', 'approval_status', 'payment_method', 'year', 'month')
    search_fields = (
        'user__username',
        'user__first_name',
        'user__last_name',
        'user__email',
        'reference',
    )
    autocomplete_fields = ('user', 'recorded_by')
    ordering = ('-date_paid',)


@admin.register(OfferingCategory)
class OfferingCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'category_type', 'is_active')
    list_filter = ('category_type', 'is_active')
    search_fields = ('name',)


@admin.register(OfferingRecord)
class OfferingRecordAdmin(admin.ModelAdmin):
    list_display = ('category', 'zone', 'deacon_group', 'amount', 'approval_status', 'service_date', 'month', 'year', 'recorded_by')
    list_filter = ('category', 'zone', 'approval_status', 'month', 'year')
    autocomplete_fields = ('category', 'zone', 'deacon_group', 'recorded_by')


@admin.register(FundraisingCampaign)
class FundraisingCampaignAdmin(admin.ModelAdmin):
    list_display = ('name', 'target_amount', 'start_date', 'end_date', 'is_active')
    list_filter = ('is_active',)
    search_fields = ('name',)


@admin.register(FundraisingContribution)
class FundraisingContributionAdmin(admin.ModelAdmin):
    list_display = ('campaign', 'contributor', 'zone', 'amount', 'approval_status', 'contribution_date', 'recorded_by')
    list_filter = ('campaign', 'zone', 'approval_status', 'contribution_date')
    autocomplete_fields = ('campaign', 'contributor', 'zone', 'recorded_by')


@admin.register(ChurchAssetCategory)
class ChurchAssetCategoryAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)


@admin.register(ChurchAsset)
class ChurchAssetAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'quantity', 'location', 'estimated_value', 'status', 'approval_status')
    list_filter = ('category', 'status', 'approval_status')
    search_fields = ('name', 'serial_number', 'location')


@admin.register(ActionApprovalLog)
class ActionApprovalLogAdmin(admin.ModelAdmin):
    list_display = ('action_area', 'action_type', 'entity_type', 'entity_label', 'performed_by', 'approval_status', 'approved_by', 'created_at')
    list_filter = ('action_area', 'action_type', 'approval_status', 'created_at')
    search_fields = ('entity_type', 'entity_label', 'description', 'performed_by__username', 'approved_by__username')
    readonly_fields = ('created_at', 'approved_at')
