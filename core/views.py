from django.shortcuts import render

# Create your views here.
from django.shortcuts import render, get_object_or_404, redirect
from django.views.generic import ListView, DetailView, TemplateView, CreateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from django.utils.text import slugify
from datetime import date, timedelta
from django.db.models import Count, Sum
from accounts.models import ChurchBranch, ChurchLeader, UserProfile, Zone
from .models import (
    EventCategory, MinistryMember, SiteConfig, HeroSlide, ServiceTime, Ministry, 
    Event, EventRegistration, BibleVerse, Testimonial, 
    GalleryImage, ContactMessage, Tithe
)
from .forms import (
    ChurchBranchForm,
    ChurchLeaderForm,
    ContactForm,
    ContactMessageStatusForm,
    EventForm,
    EventRegistrationForm,
    MinistryForm,
    OfficerMemberCreateForm,
    ZoneForm,
)
from .mixins import SiteConfigMixin  # Import the mixin


def is_staff_or_admin(user):
    """Check whether a user can access officer/admin tools."""
    return user.is_staff or user.is_superuser


def get_site_config():
    site_config = SiteConfig.objects.first()
    if not site_config:
        site_config = SiteConfig.objects.create()
    return site_config


def paginate_queryset(request, queryset, per_page=12):
    paginator = Paginator(queryset, per_page)
    return paginator.get_page(request.GET.get('page'))


def generate_unique_slug(model, value, instance_id=None):
    base_slug = slugify(value) or 'item'
    slug = base_slug
    counter = 1
    queryset = model.objects.all()
    if instance_id:
        queryset = queryset.exclude(pk=instance_id)
    while queryset.filter(slug=slug).exists():
        counter += 1
        slug = f'{base_slug}-{counter}'
    return slug


def build_officer_form_context(site_config, active_section, page_title, page_intro, form, cancel_url):
    return {
        'site_config': site_config,
        'active_section': active_section,
        'page_title': page_title,
        'page_intro': page_intro,
        'form': form,
        'cancel_url': cancel_url,
    }

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
            'hero_items': hero_slides,
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
            'other_ministries': Ministry.objects.filter(status='active').exclude(pk=ministry.pk).order_by('order', 'name')[:5],
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

    if is_staff_or_admin(user):
        return redirect('core:officer_dashboard')

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


@login_required
@user_passes_test(is_staff_or_admin)
def officer_dashboard(request):
    """Management dashboard for officers, staff, and admins."""
    user = request.user
    current_hour = timezone.localtime().hour
    if 5 <= current_hour < 12:
        greeting = "Good morning"
    elif 12 <= current_hour < 17:
        greeting = "Good afternoon"
    else:
        greeting = "Good evening"

    site_config = get_site_config()

    member_profiles = UserProfile.objects.select_related(
        'user', 'zone', 'ministry_role'
    ).order_by('-joined_at', '-id')
    active_members = User.objects.filter(is_active=True)

    profile_attention = member_profiles.filter(
        Q(phone='') |
        Q(church_branch='') |
        Q(zone__isnull=True) |
        Q(date_of_birth__isnull=True)
    ).select_related('user', 'zone')[:8]

    upcoming_events = Event.objects.filter(
        status='published',
        start_date__gte=date.today()
    ).select_related('category').order_by('start_date', 'start_time')[:6]

    ministry_breakdown = Ministry.objects.filter(status='active').annotate(
        active_member_total=Count('members', filter=Q(members__is_active=True))
    ).select_related('leader').order_by('-active_member_total', 'name')[:6]

    recent_messages = ContactMessage.objects.order_by('-created_at')[:6]
    new_messages_count = ContactMessage.objects.filter(status='new').count()
    leaders = ChurchLeader.objects.filter(is_active=True).order_by('level', 'order')[:6]
    recent_tithes = Tithe.objects.select_related('user', 'recorded_by').order_by('-date_paid')[:6]

    context = {
        'user': user,
        'greeting': greeting,
        'site_config': site_config,
        'active_section': 'dashboard',
        'stats': {
            'member_count': active_members.count(),
            'profile_count': member_profiles.count(),
            'incomplete_profiles': member_profiles.filter(
                Q(phone='') | Q(zone__isnull=True) | Q(date_of_birth__isnull=True)
            ).count(),
            'zone_count': Zone.objects.count(),
            'branch_count': ChurchBranch.objects.count(),
            'ministry_count': Ministry.objects.filter(status='active').count(),
            'leader_count': ChurchLeader.objects.filter(is_active=True).count(),
            'upcoming_event_count': Event.objects.filter(
                status='published',
                start_date__gte=date.today()
            ).count(),
            'pending_registration_count': EventRegistration.objects.filter(status='pending').count(),
            'new_message_count': new_messages_count,
            'tithe_total': Tithe.objects.filter(status='paid').aggregate(total=Sum('amount'))['total'] or 0,
        },
        'recent_members': member_profiles[:6],
        'profile_attention': profile_attention,
        'upcoming_events': upcoming_events,
        'ministry_breakdown': ministry_breakdown,
        'recent_messages': recent_messages,
        'leaders': leaders,
        'recent_tithes': recent_tithes,
        'admin_links': [
            {'label': 'Register Members', 'icon': 'fas fa-user-plus', 'route_name': 'core:officer_members', 'description': 'Angalia usajili wa members na profile zao.'},
            {'label': 'Manage Zones & Branches', 'icon': 'fas fa-map-location-dot', 'route_name': 'core:officer_structure', 'description': 'Fuata mgao wa maeneo na matawi.'},
            {'label': 'Manage Ministries', 'icon': 'fas fa-hands-holding-circle', 'route_name': 'core:officer_ministries', 'description': 'Kagua ministries na idadi ya members.'},
            {'label': 'Manage Leaders', 'icon': 'fas fa-person-chalkboard', 'route_name': 'core:officer_leaders', 'description': 'Simamia viongozi wa kanisa na huduma.'},
            {'label': 'Manage Meetings & Events', 'icon': 'fas fa-calendar-days', 'route_name': 'core:officer_events', 'description': 'Tazama mikutano, tarehe, na registrations.'},
            {'label': 'Read Messages', 'icon': 'fas fa-envelope-open-text', 'route_name': 'core:officer_messages', 'description': 'Soma ujumbe ulioingia ofisini.'},
            {'label': 'Manage Tithes', 'icon': 'fas fa-hand-holding-heart', 'route_name': 'core:admin_tithe_list', 'description': 'Kagua taarifa za zaka na sadaka.'},
        ],
    }
    return render(request, 'core/officer_dashboard.html', context)


@login_required
@user_passes_test(is_staff_or_admin)
def officer_members(request):
    site_config = get_site_config()
    member_form = OfficerMemberCreateForm()
    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'add_member':
            member_form = OfficerMemberCreateForm(request.POST)
            if member_form.is_valid():
                user = member_form.save()
                messages.success(request, f'Member {user.get_full_name() or user.username} added successfully.')
                return redirect('core:officer_members')
        elif action == 'delete_member':
            profile = get_object_or_404(UserProfile, id=request.POST.get('profile_id'))
            username = profile.user.get_full_name() or profile.user.username
            profile.user.delete()
            messages.success(request, f'Member {username} deleted successfully.')
            return redirect('core:officer_members')

    query = request.GET.get('q', '').strip()
    zone_id = request.GET.get('zone', '').strip()
    ministry_id = request.GET.get('ministry', '').strip()

    members = UserProfile.objects.select_related('user', 'zone', 'ministry_role').order_by(
        'user__first_name', 'user__last_name', 'user__username'
    )

    if query:
        members = members.filter(
            Q(user__username__icontains=query) |
            Q(user__first_name__icontains=query) |
            Q(user__last_name__icontains=query) |
            Q(user__email__icontains=query) |
            Q(phone__icontains=query) |
            Q(church_branch__icontains=query)
        )
    if zone_id:
        members = members.filter(zone_id=zone_id)
    if ministry_id:
        members = members.filter(ministry_role_id=ministry_id)

    page_obj = paginate_queryset(request, members, 12)
    context = {
        'site_config': site_config,
        'page_title': 'Officer Members',
        'page_intro': 'Usimamizi wa members waliosajiliwa na taarifa zao za msingi na kiroho ndani ya mfumo.',
        'active_section': 'members',
        'page_obj': page_obj,
        'query': query,
        'selected_zone': zone_id,
        'selected_ministry': ministry_id,
        'zones': Zone.objects.order_by('name'),
        'ministries': Ministry.objects.filter(status='active').order_by('name'),
        'total_members': members.count(),
        'incomplete_count': members.filter(
            Q(phone='') | Q(church_branch='') | Q(zone__isnull=True) | Q(date_of_birth__isnull=True)
        ).count(),
        'member_form': member_form,
    }
    return render(request, 'core/officer_members.html', context)


@login_required
@user_passes_test(is_staff_or_admin)
def officer_structure(request):
    site_config = get_site_config()
    zone_form = ZoneForm()
    branch_form = ChurchBranchForm()
    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'add_zone':
            zone_form = ZoneForm(request.POST)
            if zone_form.is_valid():
                zone_form.save()
                messages.success(request, 'Zone added successfully.')
                return redirect('core:officer_structure')
        elif action == 'add_branch':
            branch_form = ChurchBranchForm(request.POST)
            if branch_form.is_valid():
                branch_form.save()
                messages.success(request, 'Branch added successfully.')
                return redirect('core:officer_structure')
        elif action == 'delete_zone':
            zone = get_object_or_404(Zone, id=request.POST.get('zone_id'))
            if ChurchBranch.objects.filter(zone=zone).exists() or UserProfile.objects.filter(zone=zone).exists():
                messages.error(request, f'Zone {zone.name} still has branches or member profiles, so it cannot be deleted yet.')
            else:
                zone_name = zone.name
                zone.delete()
                messages.success(request, f'Zone {zone_name} deleted successfully.')
            return redirect('core:officer_structure')
        elif action == 'delete_branch':
            branch = get_object_or_404(ChurchBranch, id=request.POST.get('branch_id'))
            branch_name = branch.name
            branch.delete()
            messages.success(request, f'Branch {branch_name} deleted successfully.')
            return redirect('core:officer_structure')

    query = request.GET.get('q', '').strip()
    zones = Zone.objects.annotate(branch_count=Count('churchbranch')).order_by('name')
    branches = ChurchBranch.objects.select_related('zone').order_by('zone__name', 'name')

    if query:
        zones = zones.filter(name__icontains=query)
        branches = branches.filter(Q(name__icontains=query) | Q(zone__name__icontains=query))

    context = {
        'site_config': site_config,
        'page_title': 'Officer Structure',
        'page_intro': 'Fuata zones na church branches zilizopo ili officer aweze kujua members wanatoka wapi.',
        'active_section': 'structure',
        'zones': zones,
        'branches': branches,
        'query': query,
        'zone_count': zones.count(),
        'branch_count': branches.count(),
        'zone_form': zone_form,
        'branch_form': branch_form,
    }
    return render(request, 'core/officer_structure.html', context)


@login_required
@user_passes_test(is_staff_or_admin)
def officer_ministries(request):
    site_config = get_site_config()
    ministry_form = MinistryForm()
    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'add_ministry':
            ministry_form = MinistryForm(request.POST, request.FILES)
            if ministry_form.is_valid():
                ministry = ministry_form.save(commit=False)
                ministry.slug = generate_unique_slug(Ministry, ministry.name)
                ministry.save()
                messages.success(request, f'Ministry {ministry.name} added successfully.')
                return redirect('core:officer_ministries')
        elif action == 'delete_ministry':
            ministry = get_object_or_404(Ministry, id=request.POST.get('ministry_id'))
            if ministry.members.exists():
                messages.error(request, f'Ministry {ministry.name} still has members, so delete those memberships first.')
            else:
                ministry_name = ministry.name
                ministry.delete()
                messages.success(request, f'Ministry {ministry_name} deleted successfully.')
            return redirect('core:officer_ministries')

    query = request.GET.get('q', '').strip()
    status = request.GET.get('status', '').strip()

    ministries = Ministry.objects.annotate(
        active_member_total=Count('members', filter=Q(members__is_active=True))
    ).select_related('leader').order_by('order', 'name')

    if query:
        ministries = ministries.filter(
            Q(name__icontains=query) |
            Q(tagline__icontains=query) |
            Q(meeting_location__icontains=query)
        )
    if status:
        ministries = ministries.filter(status=status)

    context = {
        'site_config': site_config,
        'page_title': 'Officer Ministries',
        'page_intro': 'Tazama ministries, viongozi wake, ratiba, na idadi ya members hai kwa kila huduma.',
        'active_section': 'ministries',
        'ministries': ministries,
        'query': query,
        'selected_status': status,
        'total_ministries': ministries.count(),
        'featured_count': ministries.filter(is_featured=True).count(),
        'ministry_form': ministry_form,
    }
    return render(request, 'core/officer_ministries.html', context)


@login_required
@user_passes_test(is_staff_or_admin)
def officer_leaders(request):
    site_config = get_site_config()
    leader_form = ChurchLeaderForm()
    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'add_leader':
            leader_form = ChurchLeaderForm(request.POST, request.FILES)
            if leader_form.is_valid():
                leader = leader_form.save()
                messages.success(request, f'Leader {leader.full_name} added successfully.')
                return redirect('core:officer_leaders')
        elif action == 'delete_leader':
            leader = get_object_or_404(ChurchLeader, id=request.POST.get('leader_id'))
            leader_name = leader.full_name
            leader.delete()
            messages.success(request, f'Leader {leader_name} deleted successfully.')
            return redirect('core:officer_leaders')

    query = request.GET.get('q', '').strip()
    active = request.GET.get('active', '').strip()

    leaders = ChurchLeader.objects.order_by('level', 'order')
    if query:
        leaders = leaders.filter(
            Q(full_name__icontains=query) |
            Q(title__icontains=query) |
            Q(vision_message__icontains=query)
        )
    if active == 'yes':
        leaders = leaders.filter(is_active=True)
    elif active == 'no':
        leaders = leaders.filter(is_active=False)

    context = {
        'site_config': site_config,
        'page_title': 'Officer Leaders',
        'page_intro': 'Simamia viongozi wa kanisa, ngazi zao, na nafasi wanazoshikilia kwenye huduma.',
        'active_section': 'leaders',
        'leaders': leaders,
        'query': query,
        'selected_active': active,
        'leader_count': leaders.count(),
        'leader_form': leader_form,
    }
    return render(request, 'core/officer_leaders.html', context)


@login_required
@user_passes_test(is_staff_or_admin)
def officer_events(request):
    site_config = get_site_config()
    event_form = EventForm()
    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'add_event':
            event_form = EventForm(request.POST, request.FILES)
            if event_form.is_valid():
                event = event_form.save(commit=False)
                event.slug = generate_unique_slug(Event, event.title)
                event.created_by = request.user
                if event.status == 'published':
                    event.published_at = timezone.now()
                event.save()
                messages.success(request, f'Event {event.title} added successfully.')
                return redirect('core:officer_events')
        elif action == 'delete_event':
            event = get_object_or_404(Event, id=request.POST.get('event_id'))
            if event.registrations.exists():
                messages.error(request, f'Event {event.title} has registrations, so it cannot be deleted yet.')
            else:
                event_name = event.title
                event.delete()
                messages.success(request, f'Event {event_name} deleted successfully.')
            return redirect('core:officer_events')

    query = request.GET.get('q', '').strip()
    status = request.GET.get('status', '').strip()

    events = Event.objects.annotate(
        registration_count=Count('registrations')
    ).select_related('category', 'created_by').order_by('-start_date', '-start_time')

    if query:
        events = events.filter(
            Q(title__icontains=query) |
            Q(location__icontains=query) |
            Q(short_description__icontains=query)
        )
    if status:
        events = events.filter(status=status)

    page_obj = paginate_queryset(request, events, 10)
    context = {
        'site_config': site_config,
        'page_title': 'Officer Events',
        'page_intro': 'Ratibu na fuatilia mikutano, events, mahali pa kufanyika, na registrations za waumini.',
        'active_section': 'events',
        'page_obj': page_obj,
        'query': query,
        'selected_status': status,
        'upcoming_count': events.filter(start_date__gte=date.today()).count(),
        'published_count': events.filter(status='published').count(),
        'event_form': event_form,
    }
    return render(request, 'core/officer_events.html', context)


@login_required
@user_passes_test(is_staff_or_admin)
def officer_messages(request):
    site_config = get_site_config()
    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'update_status':
            message_item = get_object_or_404(ContactMessage, id=request.POST.get('message_id'))
            message_item.status = request.POST.get('status') or message_item.status
            if message_item.status == 'replied' and not message_item.replied_at:
                message_item.replied_at = timezone.now()
            message_item.save()
            messages.success(request, f'Message "{message_item.subject}" updated successfully.')
            return redirect('core:officer_messages')
        elif action == 'delete_message':
            message_item = get_object_or_404(ContactMessage, id=request.POST.get('message_id'))
            subject = message_item.subject
            message_item.delete()
            messages.success(request, f'Message "{subject}" deleted successfully.')
            return redirect('core:officer_messages')

    query = request.GET.get('q', '').strip()
    status = request.GET.get('status', '').strip()

    messages_qs = ContactMessage.objects.order_by('-created_at')
    if query:
        messages_qs = messages_qs.filter(
            Q(name__icontains=query) |
            Q(email__icontains=query) |
            Q(subject__icontains=query) |
            Q(message__icontains=query)
        )
    if status:
        messages_qs = messages_qs.filter(status=status)

    page_obj = paginate_queryset(request, messages_qs, 10)
    context = {
        'site_config': site_config,
        'page_title': 'Officer Messages',
        'page_intro': 'Soma ujumbe ulioingia, ujue hali yake, na ufuatilie mawasiliano ya ofisi.',
        'active_section': 'messages',
        'page_obj': page_obj,
        'query': query,
        'selected_status': status,
        'new_count': messages_qs.filter(status='new').count(),
        'replied_count': messages_qs.filter(status='replied').count(),
    }
    return render(request, 'core/officer_messages.html', context)


@login_required
@user_passes_test(is_staff_or_admin)
def officer_member_edit(request, profile_id):
    site_config = get_site_config()
    profile = get_object_or_404(UserProfile.objects.select_related('user'), id=profile_id)
    form = OfficerMemberCreateForm(
        request.POST or None,
        user_instance=profile.user,
        profile_instance=profile,
    )
    if request.method == 'POST' and form.is_valid():
        user = form.save()
        messages.success(request, f'Member {user.get_full_name() or user.username} updated successfully.')
        return redirect('core:officer_members')
    context = build_officer_form_context(
        site_config,
        'members',
        'Edit Member',
        'Sasisha taarifa za member, profile, na role ya officer ikiwa inahitajika.',
        form,
        'core:officer_members',
    )
    return render(request, 'core/officer_form.html', context)


@login_required
@user_passes_test(is_staff_or_admin)
def officer_zone_edit(request, zone_id):
    site_config = get_site_config()
    zone = get_object_or_404(Zone, id=zone_id)
    form = ZoneForm(request.POST or None, instance=zone)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, f'Zone {zone.name} updated successfully.')
        return redirect('core:officer_structure')
    context = build_officer_form_context(
        site_config, 'structure', 'Edit Zone', 'Badilisha jina la zone ndani ya officer portal.', form, 'core:officer_structure'
    )
    return render(request, 'core/officer_form.html', context)


@login_required
@user_passes_test(is_staff_or_admin)
def officer_branch_edit(request, branch_id):
    site_config = get_site_config()
    branch = get_object_or_404(ChurchBranch, id=branch_id)
    form = ChurchBranchForm(request.POST or None, instance=branch)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, f'Branch {branch.name} updated successfully.')
        return redirect('core:officer_structure')
    context = build_officer_form_context(
        site_config, 'structure', 'Edit Branch', 'Sasisha taarifa za branch na zone yake.', form, 'core:officer_structure'
    )
    return render(request, 'core/officer_form.html', context)


@login_required
@user_passes_test(is_staff_or_admin)
def officer_ministry_edit(request, ministry_id):
    site_config = get_site_config()
    ministry = get_object_or_404(Ministry, id=ministry_id)
    form = MinistryForm(request.POST or None, request.FILES or None, instance=ministry)
    if request.method == 'POST' and form.is_valid():
        ministry = form.save(commit=False)
        ministry.slug = generate_unique_slug(Ministry, ministry.name, instance_id=ministry.id)
        ministry.save()
        messages.success(request, f'Ministry {ministry.name} updated successfully.')
        return redirect('core:officer_ministries')
    context = build_officer_form_context(
        site_config, 'ministries', 'Edit Ministry', 'Hariri taarifa za ministry, viongozi, na ratiba zake.', form, 'core:officer_ministries'
    )
    return render(request, 'core/officer_form.html', context)


@login_required
@user_passes_test(is_staff_or_admin)
def officer_leader_edit(request, leader_id):
    site_config = get_site_config()
    leader = get_object_or_404(ChurchLeader, id=leader_id)
    form = ChurchLeaderForm(request.POST or None, request.FILES or None, instance=leader)
    if request.method == 'POST' and form.is_valid():
        leader = form.save()
        messages.success(request, f'Leader {leader.full_name} updated successfully.')
        return redirect('core:officer_leaders')
    context = build_officer_form_context(
        site_config, 'leaders', 'Edit Leader', 'Hariri taarifa za kiongozi, nafasi yake, na maelezo yake.', form, 'core:officer_leaders'
    )
    return render(request, 'core/officer_form.html', context)


@login_required
@user_passes_test(is_staff_or_admin)
def officer_event_edit(request, event_id):
    site_config = get_site_config()
    event = get_object_or_404(Event, id=event_id)
    form = EventForm(request.POST or None, request.FILES or None, instance=event)
    if request.method == 'POST' and form.is_valid():
        event = form.save(commit=False)
        event.slug = generate_unique_slug(Event, event.title, instance_id=event.id)
        if event.status == 'published' and not event.published_at:
            event.published_at = timezone.now()
        event.save()
        messages.success(request, f'Event {event.title} updated successfully.')
        return redirect('core:officer_events')
    context = build_officer_form_context(
        site_config, 'events', 'Edit Event', 'Hariri ratiba, eneo, na maelezo ya event au mkutano.', form, 'core:officer_events'
    )
    return render(request, 'core/officer_form.html', context)


@login_required
@user_passes_test(is_staff_or_admin)
def officer_message_edit(request, message_id):
    site_config = get_site_config()
    message_item = get_object_or_404(ContactMessage, id=message_id)
    form = ContactMessageStatusForm(request.POST or None, instance=message_item)
    if request.method == 'POST' and form.is_valid():
        message_obj = form.save(commit=False)
        if message_obj.status == 'replied' and not message_obj.replied_at:
            message_obj.replied_at = timezone.now()
        elif message_obj.status != 'replied':
            message_obj.replied_at = None
        message_obj.save()
        messages.success(request, f'Message "{message_obj.subject}" updated successfully.')
        return redirect('core:officer_messages')
    context = build_officer_form_context(
        site_config, 'messages', 'Edit Message', 'Sasisha ujumbe, maelezo yake, na status ya ufuatiliaji.', form, 'core:officer_messages'
    )
    return render(request, 'core/officer_form.html', context)


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
        'user_ministries': MinistryMember.objects.filter(
            user=user,
            is_active=True
        ).select_related('ministry'),
        'stats': {
            'tithe_count': Tithe.objects.filter(user=user).count(),
            'ministry_count': MinistryMember.objects.filter(user=user, is_active=True).count(),
            'event_count': EventRegistration.objects.filter(user=user).count(),
            'membership_years': max((timezone.now().date() - user.date_joined.date()).days // 365, 0),
        }
    }
    return render(request, 'core/profile.html', context)


@login_required
def create_profile(request):
    """Create a new user profile"""
    user = request.user

    site_config = SiteConfig.objects.first()
    if not site_config:
        site_config = SiteConfig.objects.create()
    
    zones = Zone.objects.all().order_by('name')
    ministry_roles = Ministry.objects.filter(status='active').order_by('name')

    # Check if profile already exists
    if UserProfile.objects.filter(user=user).exists():
        messages.info(request, 'You already have a profile.')
        return redirect('core:profile')
    
    if request.method == 'POST':
        # Get form data
        phone = request.POST.get('phone')
        church_branch = request.POST.get('church_branch')
        date_of_birth = request.POST.get('date_of_birth')
        zone_id = request.POST.get('zone')
        ministry_role_id = request.POST.get('ministry_role')
        zone = Zone.objects.filter(id=zone_id).first() if zone_id else None
        ministry_role = Ministry.objects.filter(id=ministry_role_id).first() if ministry_role_id else None
        
        # Create profile
        profile = UserProfile(
            user=user,
            phone=phone,
            church_branch=church_branch,
            zone=zone,
            ministry_role=ministry_role,
            date_of_birth=date_of_birth if date_of_birth else None,
        )
        profile.save()
        
        messages.success(request, 'Profile created successfully!')
        return redirect('core:profile')
    
    return render(request, 'core/create_profile.html', {
        'site_config': site_config,
        'zones': zones,
        'ministry_roles': ministry_roles,
        'page_title': 'Create Profile',
        'submit_label': 'Create Profile',
    })


@login_required
def edit_profile(request):
    """Edit existing user profile"""
    user = request.user
    profile = get_object_or_404(UserProfile, user=user)
    
    site_config = SiteConfig.objects.first()
    if not site_config:
        site_config = SiteConfig.objects.create()
    zones = Zone.objects.all().order_by('name')
    ministry_roles = Ministry.objects.filter(status='active').order_by('name')

    if request.method == 'POST':
        # Update profile fields
        profile.phone = request.POST.get('phone')
        profile.church_branch = request.POST.get('church_branch')
        profile.date_of_birth = request.POST.get('date_of_birth') or None
        zone_id = request.POST.get('zone')
        ministry_role_id = request.POST.get('ministry_role')
        profile.zone = Zone.objects.filter(id=zone_id).first() if zone_id else None
        profile.ministry_role = Ministry.objects.filter(id=ministry_role_id).first() if ministry_role_id else None
        
        profile.save()
        
        messages.success(request, 'Profile updated successfully!')
        return redirect('core:profile')
    
    context = {
        'profile': profile,
        'site_config': site_config,
        'zones': zones,
        'ministry_roles': ministry_roles,
        'page_title': 'Edit Profile',
        'submit_label': 'Save Changes',
    }
    return render(request, 'core/create_profile.html', context)


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

    tithes = Tithe.objects.select_related('user', 'recorded_by').order_by('-date_paid')
    
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
        'active_section': 'tithes',
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

    if is_staff_or_admin(request.user):
        tithe = get_object_or_404(Tithe, id=tithe_id)
    else:
        tithe = get_object_or_404(Tithe, id=tithe_id, user=request.user)
    
    context = {
        'tithe': tithe,
        'site_config': site_config,
    }
    return render(request, 'core/tithe_detail.html', context)
