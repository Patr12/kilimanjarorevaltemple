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
from django.db.models import Sum
from accounts.models import ChurchLeader, UserProfile
from .models import (
    EventCategory, MinistryMember, SiteConfig, HeroSlide, ServiceTime, Ministry, 
    Event, EventRegistration, BibleVerse, Testimonial, 
    GalleryImage, ContactMessage, Tithe
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
    user = request.user

    # Greeting
    current_hour = timezone.localtime().hour
    if 5 <= current_hour < 12:
        greeting = "Good morning"
    elif 12 <= current_hour < 17:
        greeting = "Good afternoon"
    else:
        greeting = "Good evening"

    site_config = SiteConfig.objects.first()
    if not site_config:
        site_config = SiteConfig.objects.create()

    # 🔹 Profile ya user
    profile = UserProfile.objects.select_related(
        'zone', 'ministry_role'
    ).filter(user=user).first()

    # 🔹 Zaka za user
    tithes = Tithe.objects.filter(user=user).order_by('-year', '-month')
    total_tithe = tithes.aggregate(total=Sum('amount'))['total'] or 0

    # 🔹 Events
    user_registrations = EventRegistration.objects.filter(
        user=user
    ).select_related('event').order_by('-registered_at')[:5]

    upcoming_events = Event.objects.filter(
        status='published',
        start_date__gte=date.today()
    ).order_by('start_date', 'start_time')[:5]

    # 🔹 Ministries
    user_ministries = MinistryMember.objects.filter(
        user=user,
        is_active=True
    ).select_related('ministry')

    context = {
        'user': user,
        'profile': profile,
        'greeting': greeting,
        'site_config': site_config,
        'user_registrations': user_registrations,
        'upcoming_events': upcoming_events,
        'user_ministries': user_ministries,
        'tithes': tithes[:5],   # last 5 records
        'total_tithe': total_tithe,
    }

    return render(request, 'core/dashboard.html', context)


# Profile Views
@login_required
def profile_view(request):
    """View and edit user profile"""
    user = request.user
    profile = UserProfile.objects.filter(user=user).first()
    site_config = SiteConfig.objects.first()
    if not site_config:
        site_config = SiteConfig.objects.create()
    
    context = {
        'user': user,
        'profile': profile,
        'site_config': site_config,
    }
    return render(request, 'core/profile.html', context)


@login_required
def create_profile(request):
    """Create a new user profile"""
    user = request.user

    site_config = SiteConfig.objects.first()
    if not site_config:
        site_config = SiteConfig.objects.create()
    
    # Check if profile already exists
    if UserProfile.objects.filter(user=user).exists():
        messages.info(request, 'You already have a profile.')
        return redirect('core:profile')
    
    if request.method == 'POST':
        # Get form data
        phone = request.POST.get('phone')
        address = request.POST.get('address')
        city = request.POST.get('city')
        date_of_birth = request.POST.get('date_of_birth')
        gender = request.POST.get('gender')
        marital_status = request.POST.get('marital_status')
        occupation = request.POST.get('occupation')
        bio = request.POST.get('bio')
        emergency_contact_name = request.POST.get('emergency_contact_name')
        emergency_contact_phone = request.POST.get('emergency_contact_phone')
        
        # Handle photo upload
        photo = request.FILES.get('photo')
        
        # Create profile
        profile = UserProfile(
            user=user,
            phone=phone,
            address=address,
            city=city,
            date_of_birth=date_of_birth if date_of_birth else None,
            gender=gender,
            marital_status=marital_status,
            occupation=occupation,
            bio=bio,
            emergency_contact_name=emergency_contact_name,
            emergency_contact_phone=emergency_contact_phone,
            photo=photo
        )
        profile.save()
        
        messages.success(request, 'Profile created successfully!')
        return redirect('core:profile')
    
    return render(request, 'core/create_profile.html')


@login_required
def edit_profile(request):
    """Edit existing user profile"""
    user = request.user
    profile = get_object_or_404(UserProfile, user=user)
    
    if request.method == 'POST':
        # Update profile fields
        profile.phone = request.POST.get('phone')
        profile.address = request.POST.get('address')
        profile.city = request.POST.get('city')
        profile.date_of_birth = request.POST.get('date_of_birth') or None
        profile.gender = request.POST.get('gender')
        profile.marital_status = request.POST.get('marital_status')
        profile.occupation = request.POST.get('occupation')
        profile.bio = request.POST.get('bio')
        profile.emergency_contact_name = request.POST.get('emergency_contact_name')
        profile.emergency_contact_phone = request.POST.get('emergency_contact_phone')
        
        # Handle photo upload
        if request.FILES.get('photo'):
            profile.photo = request.FILES.get('photo')
        
        profile.save()
        
        messages.success(request, 'Profile updated successfully!')
        return redirect('core:profile')
    
    context = {
        'profile': profile
    }
    return render(request, 'core/edit_profile.html', context)


# Tithe Views
@login_required
def tithe_history(request):
    """View user's tithe history"""
    user = request.user

    site_config = SiteConfig.objects.first()
    if not site_config:
        site_config = SiteConfig.objects.create()
    
    # Get filter parameters
    year = request.GET.get('year')
    month = request.GET.get('month')
    
    tithes = Tithe.objects.filter(user=user).order_by('-year', '-month')
    
    # Apply filters if provided
    if year:
        tithes = tithes.filter(year=year)
    if month:
        tithes = tithes.filter(month=month)
    
    # Calculate statistics
    total_amount = tithes.aggregate(total=Sum('amount'))['total'] or 0
    count = tithes.count()
    average = total_amount / count if count > 0 else 0
    
    # Get unique years for filter dropdown
    years = Tithe.objects.filter(user=user).values_list('year', flat=True).distinct().order_by('-year')
    
    # Monthly summary for chart
    monthly_summary = []
    for t in tithes[:12]:  # Last 12 records
        monthly_summary.append({
            'month': t.get_month_display(),
            'year': t.year,
            'amount': float(t.amount),
            'date': f"{t.get_month_display()} {t.year}"
        })
    
    context = {
        'tithes': tithes,
        'total_amount': total_amount,
        'site_config': site_config,
        'count': count,
        'average': average,
        'years': years,
        'selected_year': year,
        'selected_month': month,
        'monthly_summary': monthly_summary,
    }
    return render(request, 'core/tithe_history.html', context)


from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.models import User
from django.db.models import Q
from django.core.paginator import Paginator

# Helper function to check if user is staff or admin
def is_staff_or_admin(user):
    return user.is_staff or user.is_superuser

@login_required
def add_tithe(request):
    """Add a new tithe record - with staff/admin search functionality"""
    user = request.user
    is_admin = user.is_staff or user.is_superuser

    site_config = SiteConfig.objects.first()
    if not site_config:
        site_config = SiteConfig.objects.create()
    
    if request.method == 'POST':
        amount = request.POST.get('amount')
        year = request.POST.get('year')
        month = request.POST.get('month')
        payment_method = request.POST.get('payment_method')
        notes = request.POST.get('notes')
        
        # For staff/admin, get selected user from form
        if is_admin:
            selected_user_id = request.POST.get('user_id')
            if selected_user_id:
                tithe_user = User.objects.get(id=selected_user_id)
            else:
                tithe_user = user
        else:
            tithe_user = user
        
        # Check if tithe for this month/year already exists for this user
        existing_tithe = Tithe.objects.filter(
            user=tithe_user,
            year=year,
            month=month
        ).first()
        
        if existing_tithe:
            messages.warning(request, f'Tithe for {month}/{year} already exists for {tithe_user.username}!')
            return redirect('core:tithe_history')
        
        # Create new tithe
        tithe = Tithe(
            user=tithe_user,
            amount=amount,
            year=year,
            month=month,
            payment_method=payment_method,
            notes=notes,
            status='paid',
            recorded_by=user,  # Track who recorded it
            date_paid=timezone.now()
        )
        tithe.save()
        
        messages.success(request, f'Tithe recorded successfully for {tithe_user.username}!')
        return redirect('core:tithe_history')
    
    # GET request - show form
    from datetime import datetime
    current_year = datetime.now().year
    current_month = datetime.now().month
    
    context = {
        'current_year': current_year,
        'site_config': site_config,
        'current_month': current_month,
        'years': range(current_year - 5, current_year + 1),
        'months': [
            (1, 'January'), (2, 'February'), (3, 'March'), (4, 'April'),
            (5, 'May'), (6, 'June'), (7, 'July'), (8, 'August'),
            (9, 'September'), (10, 'October'), (11, 'November'), (12, 'December')
        ],
        'is_admin': is_admin,
    }
    
    return render(request, 'core/add_tithe.html', context)


@login_required
@user_passes_test(is_staff_or_admin)
def search_users(request):
    """Search users for staff/admin to add tithe"""
    site_config = SiteConfig.objects.first()
    if not site_config:
        site_config = SiteConfig.objects.create()

    query = request.GET.get('q', '')
    users = []
    
    if query:
        users = User.objects.filter(
            Q(username__icontains=query) |
            Q(first_name__icontains=query) |
            Q(last_name__icontains=query) |
            Q(email__icontains=query)
        ).filter(is_active=True)[:10]  # Limit to 10 results
    
    # Get recent tithe stats for each user
    user_data = []
    for user in users:
        recent_tithe = Tithe.objects.filter(user=user).order_by('-year', '-month').first()
        total_tithe = Tithe.objects.filter(user=user).aggregate(total=Sum('amount'))['total'] or 0
        
        user_data.append({
            'user': user,
            'recent_tithe': recent_tithe,
            'total_tithe': total_tithe,
            'full_name': user.get_full_name() or user.username,
        })
    
    return render(request, 'core/search_users.html', {
        'users': user_data,
        'query': query,
        'site_config': site_config,
    })

from django.http import JsonResponse

@login_required
@user_passes_test(is_staff_or_admin)
def search_users_api(request):
    """JSON API for searching users (for AJAX)"""
    query = request.GET.get('q', '')
    
    if len(query) < 2:
        return JsonResponse({'users': []})
    
    users = User.objects.filter(
        Q(username__icontains=query) |
        Q(first_name__icontains=query) |
        Q(last_name__icontains=query) |
        Q(email__icontains=query)
    ).filter(is_active=True)[:10]
    
    user_list = []
    for user in users:
        total_tithe = Tithe.objects.filter(user=user).aggregate(total=Sum('amount'))['total'] or 0
        user_list.append({
            'id': user.id,
            'username': user.username,
            'full_name': user.get_full_name() or user.username,
            'email': user.email,
            'is_staff': user.is_staff,
            'is_superuser': user.is_superuser,
            'total_tithe': float(total_tithe),
        })
    
    return JsonResponse({'users': user_list})
@login_required
@user_passes_test(is_staff_or_admin)
def admin_tithe_list(request):
    """View all tithes with filters for staff/admin"""
    # Badilisha order_by kutoka '-created_at' kwenda '-date_paid'
    site_config = SiteConfig.objects.first()
    if not site_config:
        site_config = SiteConfig.objects.create()

    tithes = Tithe.objects.select_related('user').order_by('-date_paid')
    
    # Apply filters
    user_id = request.GET.get('user_id')
    year = request.GET.get('year')
    month = request.GET.get('month')
    status = request.GET.get('status')
    
    if user_id:
        tithes = tithes.filter(user_id=user_id)
    if year:
        tithes = tithes.filter(year=year)
    if month:
        tithes = tithes.filter(month=month)
    if status:
        tithes = tithes.filter(status=status)
    
    # Pagination
    paginator = Paginator(tithes, 20)
    page = request.GET.get('page', 1)
    tithes_page = paginator.get_page(page)
    
    # Get all users for filter dropdown
    users = User.objects.filter(is_active=True).order_by('username')
    
    # Get years for filter
    years = Tithe.objects.values_list('year', flat=True).distinct().order_by('-year')
    
    context = {
        'tithes': tithes_page,
        'users': users,
        'years': years,
        'site_config': site_config,
        'selected_user': user_id,
        'selected_month': month,
        'selected_year': year,
        'selected_status': status,
    }
    return render(request, 'core/admin_tithe_list.html', context)


@login_required
def tithe_detail(request, tithe_id):
    """View details of a specific tithe"""
    site_config = SiteConfig.objects.first()
    if not site_config:
        site_config = SiteConfig.objects.create()

    tithe = get_object_or_404(Tithe, id=tithe_id, user=request.user)
    
    context = {
        'tithe': tithe,
        'site_config': site_config,
    }
    return render(request, 'core/tithe_detail.html', context)