from django.shortcuts import render

# Create your views here.
from django.shortcuts import render, get_object_or_404, redirect
from django.views.generic import ListView, DetailView, TemplateView, CreateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q
from django.utils import timezone
from datetime import date, timedelta

from accounts.models import ChurchLeader
from .models import (
    EventCategory, MinistryMember, SiteConfig, HeroSlide, ServiceTime, Ministry, 
    Event, EventRegistration, BibleVerse, Testimonial, 
    GalleryImage, ContactMessage
)
from .forms import ContactForm, EventRegistrationForm
from .mixins import SiteConfigMixin  # Import the mixin

class HomeView(TemplateView):
    """Homepage view"""
    template_name = 'home.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Get site configuration
        site_config = SiteConfig.objects.first()
        if not site_config:
            site_config = SiteConfig.objects.create()
        
        # Get active hero slides
        hero_slides = HeroSlide.objects.filter(is_active=True).order_by('order')
        
        # Get service times
        service_times = ServiceTime.objects.filter(is_active=True).order_by('order')
        
        # Get featured ministries
        featured_ministries = Ministry.objects.filter(
            is_featured=True,
            status='active'
        ).order_by('order')[:6]
        
        # Get upcoming events
        upcoming_events = Event.objects.filter(
            status='published',
            start_date__gte=date.today()
        ).order_by('start_date', 'start_time')[:4]
        
        # Get featured events
        featured_events = Event.objects.filter(
            status='published',
            is_featured=True,
            start_date__gte=date.today()
        ).order_by('start_date')[:3]
        
        # Get today's Bible verse
        todays_verse = BibleVerse.objects.filter(
            display_on_homepage=True
        ).order_by('-display_date').first()
        
        # Get testimonials
        testimonials = Testimonial.objects.filter(is_active=True).order_by('order')[:3]
        
        # Get gallery images
        gallery_images = GalleryImage.objects.filter(
            is_featured=True
        ).order_by('-uploaded_at')[:8]
        
        context.update({
            'site_config': site_config,
            'hero_slides': hero_slides,
            'service_times': service_times,
            'featured_ministries': featured_ministries,
            'upcoming_events': upcoming_events,
            'featured_events': featured_events,
            'todays_verse': todays_verse,
            'testimonials': testimonials,
            'gallery_images': gallery_images,
        })
        
        return context

class ServiceTimesView(SiteConfigMixin, ListView):
    """Service times page"""
    model = ServiceTime
    template_name = 'core/services.html'
    context_object_name = 'services'
    
    
    def get_queryset(self):
        return ServiceTime.objects.filter(is_active=True).order_by('day_of_week', 'start_time')
    
    def get_context_data(self, **kwargs):
         # Get site configuration
        site_config = SiteConfig.objects.first()
        if not site_config:
            site_config = SiteConfig.objects.create()
        context = super().get_context_data(**kwargs)
        context['days_of_week'] = dict(ServiceTime.DAYS_OF_WEEK)
        return context

class MinistriesView(SiteConfigMixin, ListView):
    """Ministries listing page"""
    model = Ministry
    template_name = 'ministries/ministry_list.html'
    context_object_name = 'ministries'
    paginate_by = 12
    
    def get_queryset(self):
        return Ministry.objects.filter(status='active').order_by('order', 'name')

class MinistryDetailView(SiteConfigMixin,DetailView):
    """Ministry detail page"""
    model = Ministry
    template_name = 'ministries/ministry_detail.html'
    context_object_name = 'ministry'
    slug_field = 'slug'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        ministry = self.object
        
        # Get related events
        related_events = Event.objects.filter(
            status='published',
            start_date__gte=date.today()
        ).filter(
            Q(category__name__icontains=ministry.name) | 
            Q(description__icontains=ministry.name)
        ).distinct()[:5]
        
        # Get active members
        active_members = ministry.members.filter(is_active=True).select_related('user')
        
        context.update({
            'related_events': related_events,
            'active_members': active_members,
        })
        
        return context

class EventsView(SiteConfigMixin, ListView):
    """Events listing page"""
    model = Event
    template_name = 'events/event_list.html'
    context_object_name = 'events'
    paginate_by = 12
    
    def get_queryset(self):
        queryset = Event.objects.filter(status='published')
        
        # Filter by category if provided
        category_slug = self.request.GET.get('category')
        if category_slug:
            queryset = queryset.filter(category__slug=category_slug)
        
        # Filter by upcoming/past
        filter_type = self.request.GET.get('filter', 'upcoming')
        if filter_type == 'upcoming':
            queryset = queryset.filter(start_date__gte=date.today())
        elif filter_type == 'past':
            queryset = queryset.filter(start_date__lt=date.today())
        
        return queryset.order_by('start_date', 'start_time')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['categories'] = EventCategory.objects.all()
        context['filter'] = self.request.GET.get('filter', 'upcoming')
        return context

class EventDetailView(SiteConfigMixin, DetailView):
    """Event detail page"""
    model = Event
    template_name = 'events/event_detail.html'
    context_object_name = 'event'
    slug_field = 'slug'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        event = self.object
        
        # Check if user is registered
        user_registered = False
        if self.request.user.is_authenticated:
            user_registered = EventRegistration.objects.filter(
                event=event,
                email=self.request.user.email
            ).exists()
        
        # Get remaining spots
        if event.max_attendees > 0:
            registered_count = event.registrations.filter(status='confirmed').count()
            remaining_spots = event.max_attendees - registered_count
        else:
            remaining_spots = "Unlimited"
        
        context.update({
            'user_registered': user_registered,
            'remaining_spots': remaining_spots,
            'registration_open': (
                event.requires_registration and 
                (not event.registration_deadline or event.registration_deadline > timezone.now()) and
                event.status == 'published'
            ),
        })
        
        return context

class EventRegisterView(LoginRequiredMixin, CreateView):
    """Event registration view"""
    model = EventRegistration
    form_class = EventRegistrationForm
    template_name = 'events/event_register.html'
    
    def dispatch(self, request, *args, **kwargs):
        self.event = get_object_or_404(Event, slug=kwargs['slug'], status='published')
        
        # Check if registration is open
        if not self.event.requires_registration:
            messages.error(request, "This event does not require registration.")
            return redirect(self.event.get_absolute_url())
        
        if self.event.registration_deadline and self.event.registration_deadline < timezone.now():
            messages.error(request, "Registration for this event has closed.")
            return redirect(self.event.get_absolute_url())
        
        # Check if user is already registered
        if EventRegistration.objects.filter(event=self.event, email=request.user.email).exists():
            messages.info(request, "You are already registered for this event.")
            return redirect(self.event.get_absolute_url())
        
        # Check if event is full
        if self.event.max_attendees > 0:
            registered_count = self.event.registrations.filter(status='confirmed').count()
            if registered_count >= self.event.max_attendees:
                messages.error(request, "This event is fully booked.")
                return redirect(self.event.get_absolute_url())
        
        return super().dispatch(request, *args, **kwargs)
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['event'] = self.event
        kwargs['user'] = self.request.user
        return kwargs
    
    def form_valid(self, form):
        form.instance.event = self.event
        form.instance.user = self.request.user
        response = super().form_valid(form)
        messages.success(self.request, "You have successfully registered for this event!")
        return response
    
    def get_success_url(self):
        return self.event.get_absolute_url()

class AboutView(SiteConfigMixin, TemplateView):
    """About page"""
    template_name = 'core/about.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Get statistics
        total_members = MinistryMember.objects.filter(is_active=True).count()
        total_ministries = Ministry.objects.filter(status='active').count()
        upcoming_events = Event.objects.filter(
            status='published',
            start_date__gte=date.today()
        ).count()
        
        # Get testimonials
        testimonials = Testimonial.objects.filter(is_active=True).order_by('order')
        leaders = ChurchLeader.objects.filter(is_active=True).order_by('level', 'order')
        
        context.update({
            'total_members': total_members,
            'total_ministries': total_ministries,
            'upcoming_events': upcoming_events,
            'testimonials': testimonials,
            'leaders': leaders,
        })
        
        return context

class ContactView(SiteConfigMixin,CreateView):
    """Contact page"""
    model = ContactMessage
    form_class = ContactForm
    template_name = 'core/contact.html'
    success_url = '/contact/'
    
    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, "Thank you for your message! We will get back to you soon.")
        return response

class GalleryView(SiteConfigMixin,ListView):
    """Gallery page"""
    model = GalleryImage
    template_name = 'core/gallery.html'
    context_object_name = 'images'
    paginate_by = 20
    
    def get_queryset(self):
        queryset = GalleryImage.objects.all()
        
        # Filter by category if provided
        category = self.request.GET.get('category')
        if category:
            queryset = queryset.filter(category=category)
        
        return queryset.order_by('-uploaded_at')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['categories'] = GalleryImage.objects.values_list(
            'category', flat=True
        ).distinct().exclude(category__isnull=True).exclude(category='')
        return context

@login_required
def dashboard(request):
    """User dashboard"""
    user = request.user
     # TIME-BASED GREETING
    current_hour = timezone.localtime().hour

    if 5 <= current_hour < 12:
        greeting = "Good morning"
    elif 12 <= current_hour < 17:
        greeting = "Good afternoon"
    else:
        greeting = "Good evening"

     # Get site configuration
    site_config = SiteConfig.objects.first()
    if not site_config:
            site_config = SiteConfig.objects.create()    
    
    # Get user's event registrations
    user_registrations = EventRegistration.objects.filter(
        user=user
    ).select_related('event').order_by('-registered_at')[:5]
    
    # Get upcoming events
    upcoming_events = Event.objects.filter(
        status='published',
        start_date__gte=date.today()
    ).order_by('start_date', 'start_time')[:5]
    
    # Get user's ministries
    user_ministries = MinistryMember.objects.filter(
        user=user,
        is_active=True
    ).select_related('ministry')
    
    context = {
        'user': user,
        'greeting': greeting,
        'site_config': site_config,
        'user_registrations': user_registrations,
        'upcoming_events': upcoming_events,
        'user_ministries': user_ministries,
    }
    
    return render(request, 'core/dashboard.html', context)