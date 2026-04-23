from django.shortcuts import render

# Create your views here.
from django.shortcuts import render, get_object_or_404, redirect
from django.views.generic import ListView, DetailView, TemplateView, CreateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from django.utils.text import slugify
from datetime import date, timedelta
from decimal import Decimal
from django.db.models import Count, Sum
from accounts.models import (
    ChurchBranch,
    ChurchLeader,
    DeaconGroup,
    FamilyMember,
    UserProfile,
    Zone,
    ZoneLeadership,
)
from .models import (
    EventCategory, MinistryMember, SiteConfig, HeroSlide, ServiceTime, Ministry, 
    Event, EventRegistration, BibleVerse, Testimonial, 
    GalleryImage, ContactMessage, Tithe, OfferingRecord, FundraisingCampaign,
    FundraisingContribution, ChurchAsset, ActionApprovalLog
)
from .forms import (
    ChurchBranchForm,
    ChurchLeaderForm,
    ContactForm,
    ContactMessageStatusForm,
    ChurchAssetForm,
    EventForm,
    EventRegistrationForm,
    FamilyMemberForm,
    MinistryForm,
    OfficerMemberCreateForm,
    OfferingRecordForm,
    FundraisingContributionForm,
    UserRoleAssignmentForm,
    ZoneLeadershipForm,
    DeaconGroupForm,
    ZoneForm,
)
from .mixins import SiteConfigMixin  # Import the mixin


def is_staff_or_admin(user):
    """Check whether a user can access officer/admin tools."""
    if user.is_superuser or user.is_staff:
        return True
    profile = getattr(user, 'userprofile', None)
    return bool(profile and (profile.is_management_role or profile.is_finance_role or profile.can_manage_full_system))


def get_user_profile(user):
    return UserProfile.objects.select_related('zone', 'ministry_role').filter(user=user).first()


def is_management_role(user):
    profile = get_user_profile(user)
    return bool(profile and profile.role in {'pastor', 'assistant_pastor', 'elder_council', 'institution_manager'})


def is_financial_role(user):
    profile = get_user_profile(user)
    return bool(profile and profile.role in {'secretary', 'accountant', 'zone_leader', 'deacon_leader'})


def can_manage_all_records(user):
    profile = get_user_profile(user)
    return bool(user.is_superuser or (profile and profile.role in {'pastor', 'secretary'}))


def can_add_records(user):
    profile = get_user_profile(user)
    return bool(user.is_superuser or (profile and profile.role in {'pastor', 'secretary', 'assistant_pastor', 'accountant', 'zone_leader', 'deacon_leader'}))


def get_user_scope(profile, user):
    zone_scope = None
    deacon_scope = None
    if not profile:
        return zone_scope, deacon_scope
    if profile.role == 'zone_leader':
        zone_scope = profile.zone
    elif profile.role == 'deacon_leader':
        deacon_scope = DeaconGroup.objects.filter(leader=user, is_active=True).select_related('zone').first()
        zone_scope = deacon_scope.zone if deacon_scope else profile.zone
    return zone_scope, deacon_scope


def filter_members_by_scope(queryset, zone_scope=None, deacon_scope=None):
    if zone_scope:
        queryset = queryset.filter(zone=zone_scope)
    if deacon_scope:
        queryset = queryset.filter(deacon_group=deacon_scope)
    return queryset


def filter_tithes_by_scope(queryset, zone_scope=None, deacon_scope=None):
    if zone_scope:
        queryset = queryset.filter(user__userprofile__zone=zone_scope)
    return queryset


def filter_contributions_by_scope(queryset, zone_scope=None, deacon_scope=None):
    if zone_scope:
        queryset = queryset.filter(Q(zone=zone_scope) | Q(zone__isnull=True))
    if deacon_scope:
        queryset = queryset.filter(Q(deacon_group=deacon_scope) | Q(deacon_group__isnull=True))
    return queryset


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


MONTH_LABELS = {
    1: 'January',
    2: 'February',
    3: 'March',
    4: 'April',
    5: 'May',
    6: 'June',
    7: 'July',
    8: 'August',
    9: 'September',
    10: 'October',
    11: 'November',
    12: 'December',
}


def serialize_value(value):
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, (date, timezone.datetime)):
        return value.isoformat()
    if hasattr(value, 'pk'):
        return str(value)
    return value


def snapshot_instance(instance, fields):
    data = {}
    for field in fields:
        data[field] = serialize_value(getattr(instance, field, None))
    return data


def create_action_log(request_user, action_area, action_type, entity_type, entity_id, entity_label, description='', previous_data=None, new_data=None):
    approval_status = 'auto_approved' if can_manage_all_records(request_user) else 'pending'
    approved_by = request_user if approval_status == 'auto_approved' else None
    approved_at = timezone.now() if approval_status == 'auto_approved' else None
    return ActionApprovalLog.objects.create(
        action_area=action_area,
        action_type=action_type,
        entity_type=entity_type,
        entity_id=str(entity_id or ''),
        entity_label=entity_label,
        description=description,
        previous_data=previous_data or {},
        new_data=new_data or {},
        performed_by=request_user,
        approved_by=approved_by,
        approved_at=approved_at,
        approval_status=approval_status,
    )


def get_record_approval_status(user):
    return 'auto_approved' if can_manage_all_records(user) else 'pending'


def approved_record_filter():
    return Q(approval_status__in=['approved', 'auto_approved'])


def apply_log_decision_to_entity(log_item, decision):
    model_map = {
        'Tithe': Tithe,
        'OfferingRecord': OfferingRecord,
        'FundraisingContribution': FundraisingContribution,
        'ChurchAsset': ChurchAsset,
    }
    model = model_map.get(log_item.entity_type)
    if not model or not log_item.entity_id:
        return
    try:
        obj = model.objects.filter(pk=log_item.entity_id).first()
    except Exception:
        obj = None
    if not obj or not hasattr(obj, 'approval_status'):
        return
    obj.approval_status = 'approved' if decision == 'approve' else 'rejected'
    obj.save(update_fields=['approval_status'])


def build_dashboard_notifications(profile, request_user):
    if not profile:
        return []
    if profile.role in {'pastor', 'secretary'}:
        pending_logs = ActionApprovalLog.objects.filter(approval_status='pending').count()
        return [{
            'title': 'Pending approvals',
            'value': pending_logs,
            'description': 'Records zinazosubiri approval yako.',
            'url': 'core:action_log_dashboard',
        }]
    if profile.role in {'accountant', 'zone_leader', 'deacon_leader', 'institution_manager', 'assistant_pastor'}:
        my_pending = ActionApprovalLog.objects.filter(performed_by=request_user, approval_status='pending').count()
        return [{
            'title': 'Awaiting approval',
            'value': my_pending,
            'description': 'Records ulizoweka zikisubiri pastor/secretary.',
            'url': 'core:action_log_dashboard',
        }]
    return []


def build_financial_report_data(profile, request_user, year, month=None):
    zone_scope, deacon_scope = get_user_scope(profile, request_user)
    tithes = filter_tithes_by_scope(Tithe.objects.filter(year=year, status='paid').filter(approved_record_filter()), zone_scope, deacon_scope)
    offerings = filter_contributions_by_scope(OfferingRecord.objects.filter(year=year).filter(approved_record_filter()), zone_scope, deacon_scope)
    contributions = FundraisingContribution.objects.filter(contribution_date__year=year).filter(approved_record_filter())
    if zone_scope:
        contributions = contributions.filter(Q(zone=zone_scope) | Q(zone__isnull=True))

    if month:
        tithes = tithes.filter(month=month)
        offerings = offerings.filter(month=month)
        contributions = contributions.filter(contribution_date__month=month)

    weekly_offering_summary = []
    for row in offerings.values('week_label').annotate(total=Sum('amount')).order_by('week_label'):
        weekly_offering_summary.append({'label': row['week_label'] or 'Unspecified Week', 'total': row['total'] or 0})

    monthly_offering_summary = []
    for row in offerings.values('month').annotate(total=Sum('amount')).order_by('month'):
        monthly_offering_summary.append({'label': MONTH_LABELS.get(row['month'], row['month']), 'total': row['total'] or 0})

    weekly_contribution_summary = []
    for row in contributions.values('week_label').annotate(total=Sum('amount')).order_by('week_label'):
        weekly_contribution_summary.append({'label': row['week_label'] or 'Unspecified Week', 'total': row['total'] or 0})

    category_breakdown = []
    for row in offerings.values('category__name').annotate(total=Sum('amount')).order_by('category__name'):
        category_breakdown.append({
            'label': row['category__name'] or 'General Offering',
            'total': row['total'] or 0,
        })

    period_summary = []
    tithe_by_month = {item['month']: item['total'] or 0 for item in tithes.values('month').annotate(total=Sum('amount'))}
    offering_by_month = {item['month']: item['total'] or 0 for item in offerings.values('month').annotate(total=Sum('amount'))}
    contribution_by_month = {
        item['contribution_date__month']: item['total'] or 0
        for item in contributions.values('contribution_date__month').annotate(total=Sum('amount'))
    }
    months_in_scope = set(tithe_by_month.keys()) | set(offering_by_month.keys()) | set(contribution_by_month.keys())
    for month_number in sorted(month_value for month_value in months_in_scope if month_value):
        tithe_amount = tithe_by_month.get(month_number, 0)
        offering_amount = offering_by_month.get(month_number, 0)
        contribution_amount = contribution_by_month.get(month_number, 0)
        period_summary.append({
            'label': MONTH_LABELS.get(month_number, month_number),
            'tithe_total': tithe_amount,
            'offering_total': offering_amount,
            'contribution_total': contribution_amount,
            'gross_total': tithe_amount + offering_amount + contribution_amount,
        })

    tithe_total = tithes.aggregate(total=Sum('amount'))['total'] or 0
    offering_total = offerings.aggregate(total=Sum('amount'))['total'] or 0
    contribution_total = contributions.aggregate(total=Sum('amount'))['total'] or 0

    return {
        'zone_scope': zone_scope,
        'deacon_scope': deacon_scope,
        'tithes': tithes,
        'offerings': offerings,
        'contributions': contributions,
        'tithe_total': tithe_total,
        'offering_total': offering_total,
        'contribution_total': contribution_total,
        'weekly_offering_summary': weekly_offering_summary,
        'monthly_offering_summary': monthly_offering_summary,
        'weekly_contribution_summary': weekly_contribution_summary,
        'category_breakdown': category_breakdown,
        'period_summary': period_summary,
        'gross_total': tithe_total + offering_total + contribution_total,
    }


def build_scope_dashboard_context(profile, request_user):
    current_year = timezone.now().year
    report_data = build_financial_report_data(profile, request_user, current_year)
    member_qs = UserProfile.objects.select_related('user', 'zone', 'deacon_group').all()
    member_qs = filter_members_by_scope(member_qs, report_data['zone_scope'], report_data['deacon_scope'])
    tithe_qs = filter_tithes_by_scope(Tithe.objects.select_related('user', 'recorded_by').order_by('-date_paid'), report_data['zone_scope'], report_data['deacon_scope'])
    offering_qs = filter_contributions_by_scope(OfferingRecord.objects.select_related('category', 'zone', 'deacon_group').order_by('-service_date'), report_data['zone_scope'], report_data['deacon_scope'])
    return {
        'zone_scope': report_data['zone_scope'],
        'deacon_scope': report_data['deacon_scope'],
        'stats': {
            'members': member_qs.count(),
            'tithe_total': report_data['tithe_total'],
            'offering_total': report_data['offering_total'],
            'fundraising_total': report_data['contribution_total'],
            'active_campaigns': FundraisingCampaign.objects.filter(is_active=True).count(),
        },
        'recent_members': member_qs.order_by('-joined_at')[:6],
        'recent_tithes': tithe_qs[:6],
        'recent_offerings': offering_qs[:6],
        'active_campaigns': FundraisingCampaign.objects.filter(is_active=True).order_by('-start_date')[:6],
        'recent_logs': ActionApprovalLog.objects.filter(
            performed_by=request_user,
            action_area__in=['roles', 'assets', 'offerings', 'tithes'],
        ).order_by('-created_at')[:6],
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
    profile = get_user_profile(user)

    if profile:
        if profile.role in {'pastor', 'assistant_pastor', 'elder_council', 'institution_manager'}:
            return redirect('core:management_dashboard')
        if profile.role in {'secretary', 'accountant'}:
            return redirect('core:financial_dashboard')
        if profile.role == 'zone_leader':
            return redirect('core:zone_leader_dashboard')
        if profile.role == 'deacon_leader':
            return redirect('core:deacon_leader_dashboard')

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

    family_members = FamilyMember.objects.filter(primary_member=profile) if profile else FamilyMember.objects.none()

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
        'family_members': family_members[:5],
        'family_count': family_members.count(),
        'notifications': build_dashboard_notifications(profile, user),
    }

    return render(request, 'core/dashboard.html', context)


@login_required
def management_dashboard(request):
    profile = get_user_profile(request.user)
    if not profile or profile.role not in {'pastor', 'assistant_pastor', 'elder_council', 'institution_manager'}:
        messages.error(request, 'You do not have permission to access the management dashboard.')
        return redirect('core:dashboard')

    site_config = get_site_config()
    total_members = UserProfile.objects.count()
    total_zones = Zone.objects.count()
    total_branches = ChurchBranch.objects.count()
    total_ministries = Ministry.objects.filter(status='active').count()
    total_assets = ChurchAsset.objects.count()
    total_events = Event.objects.filter(status='published').count()
    upcoming_events = Event.objects.filter(status='published', start_date__gte=date.today()).order_by('start_date', 'start_time')[:6]
    zone_leaders = ZoneLeadership.objects.select_related('user', 'zone').filter(is_active=True).order_by('zone__name')[:8]
    deacon_groups = DeaconGroup.objects.select_related('zone', 'leader').filter(is_active=True).order_by('zone__name', 'name')[:8]
    elders = UserProfile.objects.select_related('user').filter(role='elder_council').order_by('user__first_name', 'user__last_name')[:8]

    context = {
        'site_config': site_config,
        'profile': profile,
        'dashboard_type': 'management',
        'stats': {
            'members': total_members,
            'zones': total_zones,
            'branches': total_branches,
            'ministries': total_ministries,
            'assets': total_assets,
            'events': total_events,
        },
        'upcoming_events': upcoming_events,
        'zone_leaders': zone_leaders,
        'deacon_groups': deacon_groups,
        'elders': elders,
        'can_full_manage': profile.role == 'pastor' or request.user.is_superuser,
        'can_add_records': profile.role in {'pastor', 'assistant_pastor'} or request.user.is_superuser,
        'notifications': build_dashboard_notifications(profile, request.user),
    }
    return render(request, 'core/management_dashboard.html', context)


@login_required
def role_assignment_dashboard(request):
    profile = get_user_profile(request.user)
    if not profile or profile.role not in {'pastor', 'secretary'}:
        messages.error(request, 'You do not have permission to assign roles.')
        return redirect('core:dashboard')

    site_config = get_site_config()
    query = request.GET.get('q', '').strip()
    profiles = UserProfile.objects.select_related('user', 'zone', 'deacon_group', 'ministry_role').order_by(
        'user__first_name', 'user__last_name', 'user__username'
    )
    if query:
        profiles = profiles.filter(
            Q(user__username__icontains=query) |
            Q(user__first_name__icontains=query) |
            Q(user__last_name__icontains=query) |
            Q(role__icontains=query)
        )
    context = {
        'site_config': site_config,
        'profile': profile,
        'profiles': paginate_queryset(request, profiles, 12),
        'query': query,
    }
    return render(request, 'core/role_assignment_dashboard.html', context)


@login_required
def action_log_dashboard(request):
    profile = get_user_profile(request.user)
    if not profile or profile.role not in {'pastor', 'secretary', 'accountant'}:
        messages.error(request, 'You do not have permission to view action logs.')
        return redirect('core:dashboard')

    site_config = get_site_config()
    query = request.GET.get('q', '').strip()
    action_area = request.GET.get('area', '').strip()
    approval_status = request.GET.get('status', '').strip()
    logs = ActionApprovalLog.objects.select_related('performed_by', 'approved_by').order_by('-created_at')
    if query:
        logs = logs.filter(
            Q(entity_label__icontains=query) |
            Q(entity_type__icontains=query) |
            Q(description__icontains=query) |
            Q(performed_by__username__icontains=query) |
            Q(approved_by__username__icontains=query)
        )
    if action_area:
        logs = logs.filter(action_area=action_area)
    if approval_status:
        logs = logs.filter(approval_status=approval_status)

    if request.method == 'POST' and profile.role in {'pastor', 'secretary'}:
        log_item = get_object_or_404(ActionApprovalLog, id=request.POST.get('log_id'))
        decision = request.POST.get('decision')
        if decision == 'approve':
            log_item.approval_status = 'approved'
            log_item.approved_by = request.user
            log_item.approved_at = timezone.now()
            log_item.save(update_fields=['approval_status', 'approved_by', 'approved_at'])
            apply_log_decision_to_entity(log_item, 'approve')
            messages.success(request, 'Action log approved successfully.')
        elif decision == 'reject':
            log_item.approval_status = 'rejected'
            log_item.approved_by = request.user
            log_item.approved_at = timezone.now()
            log_item.save(update_fields=['approval_status', 'approved_by', 'approved_at'])
            apply_log_decision_to_entity(log_item, 'reject')
            messages.success(request, 'Action log rejected successfully.')
        return redirect('core:action_log_dashboard')

    context = {
        'site_config': site_config,
        'profile': profile,
        'logs': paginate_queryset(request, logs, 15),
        'query': query,
        'selected_area': action_area,
        'selected_status': approval_status,
        'can_approve': profile.role in {'pastor', 'secretary'},
        'notifications': build_dashboard_notifications(profile, request.user),
    }
    return render(request, 'core/action_log_dashboard.html', context)


@login_required
def financial_dashboard(request):
    profile = get_user_profile(request.user)
    if not profile or profile.role not in {'secretary', 'accountant'}:
        messages.error(request, 'You do not have permission to access the financial dashboard.')
        return redirect('core:dashboard')

    site_config = get_site_config()
    dashboard_data = build_scope_dashboard_context(profile, request.user)

    context = {
        'site_config': site_config,
        'profile': profile,
        'dashboard_type': 'financial',
        **dashboard_data,
        'can_full_manage': profile.role == 'secretary' or request.user.is_superuser,
        'can_edit_finance': profile.role in {'secretary', 'accountant'} or request.user.is_superuser,
        'notifications': build_dashboard_notifications(profile, request.user),
    }
    return render(request, 'core/financial_dashboard.html', context)


@login_required
def zone_leader_dashboard(request):
    profile = get_user_profile(request.user)
    if not profile or profile.role != 'zone_leader':
        messages.error(request, 'You do not have permission to access the zone leader dashboard.')
        return redirect('core:dashboard')

    site_config = get_site_config()
    dashboard_data = build_scope_dashboard_context(profile, request.user)
    context = {
        'site_config': site_config,
        'profile': profile,
        **dashboard_data,
        'dashboard_title': 'Zone Leader Dashboard',
        'notifications': build_dashboard_notifications(profile, request.user),
    }
    return render(request, 'core/zone_leader_dashboard.html', context)


@login_required
def deacon_leader_dashboard(request):
    profile = get_user_profile(request.user)
    if not profile or profile.role != 'deacon_leader':
        messages.error(request, 'You do not have permission to access the deacon leader dashboard.')
        return redirect('core:dashboard')

    site_config = get_site_config()
    dashboard_data = build_scope_dashboard_context(profile, request.user)
    context = {
        'site_config': site_config,
        'profile': profile,
        **dashboard_data,
        'dashboard_title': 'Deacon Leader Dashboard',
        'notifications': build_dashboard_notifications(profile, request.user),
    }
    return render(request, 'core/deacon_leader_dashboard.html', context)


@login_required
def financial_members(request):
    profile = get_user_profile(request.user)
    if not profile or profile.role not in {'secretary', 'accountant', 'zone_leader', 'deacon_leader'}:
        messages.error(request, 'You do not have permission to view finance members.')
        return redirect('core:dashboard')

    site_config = get_site_config()
    zone_scope, deacon_scope = get_user_scope(profile, request.user)
    members = UserProfile.objects.select_related('user', 'zone', 'deacon_group', 'ministry_role').order_by('user__first_name', 'user__last_name', 'user__username')
    members = filter_members_by_scope(members, zone_scope, deacon_scope)

    query = request.GET.get('q', '').strip()
    if query:
        members = members.filter(
            Q(user__username__icontains=query) |
            Q(user__first_name__icontains=query) |
            Q(user__last_name__icontains=query) |
            Q(tithe_card_number__icontains=query) |
            Q(phone__icontains=query)
        )

    context = {
        'site_config': site_config,
        'profile': profile,
        'members': paginate_queryset(request, members, 12),
        'query': query,
        'zone_scope': zone_scope,
        'deacon_scope': deacon_scope,
    }
    return render(request, 'core/financial_members.html', context)


@login_required
def financial_offerings(request):
    profile = get_user_profile(request.user)
    if not profile or profile.role not in {'secretary', 'accountant', 'zone_leader', 'deacon_leader'}:
        messages.error(request, 'You do not have permission to manage offerings.')
        return redirect('core:dashboard')

    site_config = get_site_config()
    zone_scope, deacon_scope = get_user_scope(profile, request.user)
    can_edit = profile.role in {'secretary', 'accountant', 'zone_leader', 'deacon_leader'} or request.user.is_superuser
    form = OfferingRecordForm()

    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'add_offering':
            if not can_edit:
                messages.error(request, 'You are not allowed to record offerings.')
                return redirect('core:financial_offerings')
            form = OfferingRecordForm(request.POST)
            if form.is_valid():
                offering = form.save(commit=False)
                if zone_scope and not offering.zone:
                    offering.zone = zone_scope
                if deacon_scope and not offering.deacon_group:
                    offering.deacon_group = deacon_scope
                offering.recorded_by = request.user
                offering.approval_status = get_record_approval_status(request.user)
                offering.save()
                create_action_log(
                    request.user,
                    'offerings',
                    'create',
                    'OfferingRecord',
                    offering.id,
                    offering.category.name,
                    description='Offering record created from dashboard.',
                    new_data=snapshot_instance(offering, ['category_id', 'zone_id', 'deacon_group_id', 'amount', 'week_label', 'month', 'year', 'service_date']),
                )
                messages.success(request, 'Offering recorded successfully.')
                return redirect('core:financial_offerings')
        elif action == 'delete_offering':
            if not can_edit:
                messages.error(request, 'You are not allowed to delete offerings.')
                return redirect('core:financial_offerings')
            offering = get_object_or_404(OfferingRecord, id=request.POST.get('offering_id'))
            previous_data = snapshot_instance(offering, ['category_id', 'zone_id', 'deacon_group_id', 'amount', 'week_label', 'month', 'year', 'service_date'])
            offering_id = offering.id
            offering_label = offering.category.name
            offering.delete()
            create_action_log(
                request.user,
                'offerings',
                'delete',
                'OfferingRecord',
                offering_id,
                offering_label,
                description='Offering record deleted from dashboard.',
                previous_data=previous_data,
            )
            messages.success(request, 'Offering deleted successfully.')
            return redirect('core:financial_offerings')

    offerings = OfferingRecord.objects.select_related('category', 'zone', 'deacon_group', 'recorded_by').order_by('-service_date', '-created_at')
    offerings = filter_contributions_by_scope(offerings, zone_scope, deacon_scope)
    context = {
        'site_config': site_config,
        'profile': profile,
        'form': form,
        'offerings': paginate_queryset(request, offerings, 12),
        'can_edit': can_edit,
        'zone_scope': zone_scope,
        'deacon_scope': deacon_scope,
    }
    return render(request, 'core/financial_offerings.html', context)


@login_required
def financial_contributions(request):
    profile = get_user_profile(request.user)
    if not profile or profile.role not in {'secretary', 'accountant', 'zone_leader', 'deacon_leader'}:
        messages.error(request, 'You do not have permission to manage contributions.')
        return redirect('core:dashboard')

    site_config = get_site_config()
    zone_scope, deacon_scope = get_user_scope(profile, request.user)
    can_edit = profile.role in {'secretary', 'accountant', 'zone_leader', 'deacon_leader'} or request.user.is_superuser
    form = FundraisingContributionForm()

    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'add_contribution':
            if not can_edit:
                messages.error(request, 'You are not allowed to record contributions.')
                return redirect('core:financial_contributions')
            form = FundraisingContributionForm(request.POST)
            if form.is_valid():
                contribution = form.save(commit=False)
                if zone_scope and not contribution.zone:
                    contribution.zone = zone_scope
                contribution.recorded_by = request.user
                contribution.approval_status = get_record_approval_status(request.user)
                contribution.save()
                create_action_log(
                    request.user,
                    'offerings',
                    'create',
                    'FundraisingContribution',
                    contribution.id,
                    contribution.campaign.name,
                    description='Contribution record created from dashboard.',
                    new_data=snapshot_instance(contribution, ['campaign_id', 'contributor_id', 'zone_id', 'amount', 'contribution_date', 'week_label']),
                )
                messages.success(request, 'Contribution recorded successfully.')
                return redirect('core:financial_contributions')
        elif action == 'delete_contribution':
            if not can_edit:
                messages.error(request, 'You are not allowed to delete contributions.')
                return redirect('core:financial_contributions')
            contribution = get_object_or_404(FundraisingContribution, id=request.POST.get('contribution_id'))
            previous_data = snapshot_instance(contribution, ['campaign_id', 'contributor_id', 'zone_id', 'amount', 'contribution_date', 'week_label'])
            contribution_id = contribution.id
            contribution_label = contribution.campaign.name
            contribution.delete()
            create_action_log(
                request.user,
                'offerings',
                'delete',
                'FundraisingContribution',
                contribution_id,
                contribution_label,
                description='Contribution record deleted from dashboard.',
                previous_data=previous_data,
            )
            messages.success(request, 'Contribution deleted successfully.')
            return redirect('core:financial_contributions')

    contributions = FundraisingContribution.objects.select_related('campaign', 'contributor', 'zone', 'recorded_by').order_by('-contribution_date', '-id')
    if zone_scope:
        contributions = contributions.filter(Q(zone=zone_scope) | Q(zone__isnull=True))
    context = {
        'site_config': site_config,
        'profile': profile,
        'form': form,
        'contributions': paginate_queryset(request, contributions, 12),
        'can_edit': can_edit,
        'zone_scope': zone_scope,
    }
    return render(request, 'core/financial_contributions.html', context)


@login_required
def asset_management(request):
    profile = get_user_profile(request.user)
    if not profile or profile.role not in {'secretary', 'accountant', 'pastor', 'institution_manager'}:
        messages.error(request, 'You do not have permission to manage church assets.')
        return redirect('core:dashboard')

    site_config = get_site_config()
    can_edit = profile.role in {'secretary', 'pastor', 'institution_manager'} or request.user.is_superuser
    form = ChurchAssetForm()
    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'add_asset':
            if not can_edit:
                messages.error(request, 'You are not allowed to add assets.')
                return redirect('core:asset_management')
            form = ChurchAssetForm(request.POST)
            if form.is_valid():
                asset = form.save()
                asset.approval_status = get_record_approval_status(request.user)
                asset.save(update_fields=['approval_status'])
                create_action_log(
                    request.user,
                    'assets',
                    'create',
                    'ChurchAsset',
                    asset.id,
                    asset.name,
                    description='Church asset created from dashboard.',
                    new_data=snapshot_instance(asset, ['name', 'category_id', 'serial_number', 'quantity', 'condition', 'location', 'estimated_value', 'status']),
                )
                messages.success(request, 'Church asset added successfully.')
                return redirect('core:asset_management')
        elif action == 'delete_asset':
            if not can_edit:
                messages.error(request, 'You are not allowed to delete assets.')
                return redirect('core:asset_management')
            asset = get_object_or_404(ChurchAsset, id=request.POST.get('asset_id'))
            previous_data = snapshot_instance(asset, ['name', 'category_id', 'serial_number', 'quantity', 'condition', 'location', 'estimated_value', 'status'])
            asset_id = asset.id
            asset_name = asset.name
            asset.delete()
            create_action_log(
                request.user,
                'assets',
                'delete',
                'ChurchAsset',
                asset_id,
                asset_name,
                description='Church asset deleted from dashboard.',
                previous_data=previous_data,
            )
            messages.success(request, 'Church asset deleted successfully.')
            return redirect('core:asset_management')

    assets = ChurchAsset.objects.select_related('category').order_by('name')
    context = {
        'site_config': site_config,
        'profile': profile,
        'form': form,
        'assets': paginate_queryset(request, assets, 12),
        'can_edit': can_edit,
    }
    return render(request, 'core/asset_management.html', context)


@login_required
def family_management(request):
    profile = get_user_profile(request.user)
    if not profile:
        messages.error(request, 'Create your profile first before registering family members.')
        return redirect('core:create_profile')

    site_config = get_site_config()
    form = FamilyMemberForm()
    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'add_family':
            form = FamilyMemberForm(request.POST)
            if form.is_valid():
                family = form.save(commit=False)
                family.primary_member = profile
                family.save()
                messages.success(request, 'Family member added successfully.')
                return redirect('core:family_management')
        elif action == 'delete_family':
            family = get_object_or_404(FamilyMember, id=request.POST.get('family_id'), primary_member=profile)
            family.delete()
            messages.success(request, 'Family member deleted successfully.')
            return redirect('core:family_management')

    family_members = FamilyMember.objects.filter(primary_member=profile).order_by('full_name')
    context = {
        'site_config': site_config,
        'profile': profile,
        'form': form,
        'family_members': family_members,
    }
    return render(request, 'core/family_management.html', context)


@login_required
def financial_reports(request):
    profile = get_user_profile(request.user)
    if not profile or profile.role not in {'secretary', 'accountant', 'zone_leader', 'deacon_leader'}:
        messages.error(request, 'You do not have permission to view reports.')
        return redirect('core:dashboard')

    site_config = get_site_config()
    year = int(request.GET.get('year') or timezone.now().year)
    month = request.GET.get('month')
    report_data = build_financial_report_data(profile, request.user, year, month)

    context = {
        'site_config': site_config,
        'profile': profile,
        'selected_year': year,
        'selected_month': month,
        'years': range(timezone.now().year - 3, timezone.now().year + 1),
        **report_data,
        'tithes': report_data['tithes'].order_by('-date_paid')[:20],
        'offerings': report_data['offerings'].order_by('-service_date')[:20],
        'contributions': report_data['contributions'].order_by('-contribution_date')[:20],
    }
    return render(request, 'core/financial_reports.html', context)


@login_required
def financial_report_pdf(request):
    profile = get_user_profile(request.user)
    if not profile or profile.role not in {'secretary', 'accountant', 'zone_leader', 'deacon_leader'}:
        messages.error(request, 'You do not have permission to export PDF reports.')
        return redirect('core:dashboard')

    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.units import mm
        from reportlab.pdfgen import canvas
    except ImportError:
        messages.error(request, 'PDF library is not installed yet. Install reportlab first, then try again.')
        return redirect('core:financial_reports')

    year = int(request.GET.get('year') or timezone.now().year)
    month = request.GET.get('month')
    report_data = build_financial_report_data(profile, request.user, year, month)
    site_config = get_site_config()

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="financial-report-{year}-{month or "full-year"}.pdf"'

    pdf = canvas.Canvas(response, pagesize=A4)
    width, height = A4
    y = height - 20 * mm

    def line(text, size=11, gap=7):
        nonlocal y
        if y < 20 * mm:
            pdf.showPage()
            y = height - 20 * mm
        pdf.setFont("Helvetica", size)
        pdf.drawString(18 * mm, y, str(text))
        y -= gap * mm

    pdf.setTitle(f"Financial Report {year}")
    line(site_config.site_name or 'Church Financial Report', size=16, gap=8)
    line(f"Prepared for: {profile.get_role_display()}", size=11)
    line(f"Year: {year} | Month: {MONTH_LABELS.get(int(month), month) if month else 'Full Year'}", size=11)
    line(f"Zone Scope: {report_data['zone_scope'].name if report_data['zone_scope'] else 'Whole Church'}", size=11)
    line(f"Deacon Scope: {report_data['deacon_scope'].name if report_data['deacon_scope'] else 'All Groups'}", size=11, gap=10)
    line("Balance Sheet Summary", size=13, gap=6)
    line(f"Tithe Income: {report_data['tithe_total']}")
    line(f"Offering Income: {report_data['offering_total']}")
    line(f"Contribution Income: {report_data['contribution_total']}")
    line(f"Gross Total: {report_data['gross_total']}", gap=10)
    line("Monthly Income Matrix", size=13, gap=6)
    for row in report_data['period_summary'][:12]:
        line(f"{row['label']}: Tithe {row['tithe_total']} | Offering {row['offering_total']} | Contribution {row['contribution_total']} | Gross {row['gross_total']}", size=10, gap=5)
    line("Offering Category Breakdown", size=13, gap=6)
    for row in report_data['category_breakdown'][:12]:
        line(f"{row['label']}: {row['total']}", size=10, gap=5)
    line("Recent Tithe Entries", size=13, gap=6)
    for item in report_data['tithes'].order_by('-date_paid')[:10]:
        line(f"{item.user.get_full_name() or item.user.username} - {item.get_month_display} {item.year} - {item.amount}", size=10, gap=5)
    pdf.save()
    return response


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
        'notifications': build_dashboard_notifications(get_user_profile(user), user),
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
    full_manage = can_manage_all_records(request.user)
    add_only = can_add_records(request.user)
    profile = get_user_profile(request.user)
    zone_scope, deacon_scope = get_user_scope(profile, request.user)
    member_form = OfficerMemberCreateForm(allow_staff_toggle=full_manage)
    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'add_member':
            if not add_only:
                messages.error(request, 'You are not allowed to register members.')
                return redirect('core:officer_members')
            member_form = OfficerMemberCreateForm(request.POST, allow_staff_toggle=full_manage)
            if member_form.is_valid():
                user = member_form.save()
                if zone_scope:
                    user.userprofile.zone = zone_scope
                    if not user.userprofile.church_branch:
                        user.userprofile.church_branch = zone_scope.name
                if deacon_scope:
                    user.userprofile.deacon_group = deacon_scope
                    user.userprofile.zone = deacon_scope.zone
                user.userprofile.save()
                messages.success(request, f'Member {user.get_full_name() or user.username} added successfully.')
                return redirect('core:officer_members')
        elif action == 'delete_member':
            if not full_manage:
                messages.error(request, 'You are not allowed to delete members.')
                return redirect('core:officer_members')
            profile = get_object_or_404(UserProfile, id=request.POST.get('profile_id'))
            username = profile.user.get_full_name() or profile.user.username
            profile.user.delete()
            messages.success(request, f'Member {username} deleted successfully.')
            return redirect('core:officer_members')

    query = request.GET.get('q', '').strip()
    zone_id = request.GET.get('zone', '').strip()
    deacon_group_id = request.GET.get('deacon_group', '').strip()
    ministry_id = request.GET.get('ministry', '').strip()

    members = UserProfile.objects.select_related('user', 'zone', 'deacon_group', 'ministry_role').order_by(
        'user__first_name', 'user__last_name', 'user__username'
    )
    members = filter_members_by_scope(members, zone_scope, deacon_scope)

    if query:
        members = members.filter(
            Q(user__username__icontains=query) |
            Q(user__first_name__icontains=query) |
            Q(user__last_name__icontains=query) |
            Q(user__email__icontains=query) |
            Q(phone__icontains=query) |
            Q(church_branch__icontains=query) |
            Q(tithe_card_number__icontains=query)
        )
    if zone_id:
        members = members.filter(zone_id=zone_id)
    if deacon_group_id:
        members = members.filter(deacon_group_id=deacon_group_id)
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
        'selected_deacon_group': deacon_group_id,
        'selected_ministry': ministry_id,
        'zones': Zone.objects.order_by('name'),
        'deacon_groups': DeaconGroup.objects.select_related('zone').filter(is_active=True).order_by('zone__name', 'name'),
        'ministries': Ministry.objects.filter(status='active').order_by('name'),
        'total_members': members.count(),
        'incomplete_count': members.filter(
            Q(phone='') | Q(church_branch='') | Q(zone__isnull=True) | Q(date_of_birth__isnull=True)
        ).count(),
        'member_form': member_form,
        'can_add_records': add_only,
        'can_full_manage': full_manage,
        'zone_scope': zone_scope,
        'deacon_scope': deacon_scope,
    }
    return render(request, 'core/officer_members.html', context)


@login_required
@user_passes_test(is_staff_or_admin)
def officer_structure(request):
    site_config = get_site_config()
    full_manage = can_manage_all_records(request.user)
    zone_form = ZoneForm()
    branch_form = ChurchBranchForm()
    leadership_form = ZoneLeadershipForm()
    deacon_group_form = DeaconGroupForm()
    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'add_zone':
            if not full_manage:
                messages.error(request, 'You are not allowed to add zones.')
                return redirect('core:officer_structure')
            zone_form = ZoneForm(request.POST)
            if zone_form.is_valid():
                zone_form.save()
                messages.success(request, 'Zone added successfully.')
                return redirect('core:officer_structure')
        elif action == 'add_branch':
            if not full_manage:
                messages.error(request, 'You are not allowed to add branches.')
                return redirect('core:officer_structure')
            branch_form = ChurchBranchForm(request.POST)
            if branch_form.is_valid():
                branch_form.save()
                messages.success(request, 'Branch added successfully.')
                return redirect('core:officer_structure')
        elif action == 'delete_zone':
            if not full_manage:
                messages.error(request, 'You are not allowed to delete zones.')
                return redirect('core:officer_structure')
            zone = get_object_or_404(Zone, id=request.POST.get('zone_id'))
            if ChurchBranch.objects.filter(zone=zone).exists() or UserProfile.objects.filter(zone=zone).exists():
                messages.error(request, f'Zone {zone.name} still has branches or member profiles, so it cannot be deleted yet.')
            else:
                zone_name = zone.name
                zone.delete()
                messages.success(request, f'Zone {zone_name} deleted successfully.')
            return redirect('core:officer_structure')
        elif action == 'delete_branch':
            if not full_manage:
                messages.error(request, 'You are not allowed to delete branches.')
                return redirect('core:officer_structure')
            branch = get_object_or_404(ChurchBranch, id=request.POST.get('branch_id'))
            branch_name = branch.name
            branch.delete()
            messages.success(request, f'Branch {branch_name} deleted successfully.')
            return redirect('core:officer_structure')
        elif action == 'add_zone_leadership':
            if not full_manage:
                messages.error(request, 'You are not allowed to assign zone leadership.')
                return redirect('core:officer_structure')
            leadership_form = ZoneLeadershipForm(request.POST)
            if leadership_form.is_valid():
                user = leadership_form.cleaned_data['user']
                zone = leadership_form.cleaned_data['zone']
                role = leadership_form.cleaned_data['role']
                ZoneLeadership.objects.update_or_create(
                    user=user,
                    zone=zone,
                    role=role,
                    defaults={'is_active': True},
                )
                profile = UserProfile.objects.filter(user=user).first()
                if profile:
                    profile.zone = zone
                    if role == 'zone_leader':
                        profile.role = 'zone_leader'
                    profile.save()
                messages.success(request, 'Zone leadership assigned successfully.')
                return redirect('core:officer_structure')
        elif action == 'delete_zone_leadership':
            if not full_manage:
                messages.error(request, 'You are not allowed to remove zone leadership.')
                return redirect('core:officer_structure')
            leadership = get_object_or_404(ZoneLeadership, id=request.POST.get('leadership_id'))
            leadership.delete()
            messages.success(request, 'Zone leadership removed successfully.')
            return redirect('core:officer_structure')
        elif action == 'add_deacon_group':
            if not full_manage:
                messages.error(request, 'You are not allowed to add deacon groups.')
                return redirect('core:officer_structure')
            deacon_group_form = DeaconGroupForm(request.POST)
            if deacon_group_form.is_valid():
                group = deacon_group_form.save()
                if group.leader:
                    profile = UserProfile.objects.filter(user=group.leader).first()
                    if profile:
                        profile.zone = group.zone
                        profile.deacon_group = group
                        profile.role = 'deacon_leader'
                        profile.save()
                messages.success(request, 'Deacon group added successfully.')
                return redirect('core:officer_structure')
        elif action == 'delete_deacon_group':
            if not full_manage:
                messages.error(request, 'You are not allowed to delete deacon groups.')
                return redirect('core:officer_structure')
            group = get_object_or_404(DeaconGroup, id=request.POST.get('deacon_group_id'))
            if group.members.exists():
                messages.error(request, f'{group.name} still has assigned members.')
            else:
                group.delete()
                messages.success(request, 'Deacon group deleted successfully.')
            return redirect('core:officer_structure')

    query = request.GET.get('q', '').strip()
    zones = Zone.objects.annotate(
        branch_count=Count('churchbranch'),
        deacon_group_count=Count('deacon_groups', distinct=True),
        member_count=Count('userprofile', distinct=True),
    ).order_by('name')
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
        'leadership_form': leadership_form,
        'deacon_group_form': deacon_group_form,
        'zone_leaderships': ZoneLeadership.objects.select_related('user', 'zone').filter(is_active=True).order_by('zone__name', 'role'),
        'deacon_groups': DeaconGroup.objects.select_related('zone', 'leader').annotate(member_count=Count('members')).order_by('zone__name', 'name'),
        'can_full_manage': full_manage,
    }
    return render(request, 'core/officer_structure.html', context)


@login_required
@user_passes_test(is_staff_or_admin)
def officer_ministries(request):
    site_config = get_site_config()
    full_manage = can_manage_all_records(request.user)
    ministry_form = MinistryForm()
    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'add_ministry':
            if not full_manage:
                messages.error(request, 'You are not allowed to add ministries.')
                return redirect('core:officer_ministries')
            ministry_form = MinistryForm(request.POST, request.FILES)
            if ministry_form.is_valid():
                ministry = ministry_form.save(commit=False)
                ministry.slug = generate_unique_slug(Ministry, ministry.name)
                ministry.save()
                messages.success(request, f'Ministry {ministry.name} added successfully.')
                return redirect('core:officer_ministries')
        elif action == 'delete_ministry':
            if not full_manage:
                messages.error(request, 'You are not allowed to delete ministries.')
                return redirect('core:officer_ministries')
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
        'can_full_manage': full_manage,
    }
    return render(request, 'core/officer_ministries.html', context)


@login_required
@user_passes_test(is_staff_or_admin)
def officer_leaders(request):
    site_config = get_site_config()
    full_manage = can_manage_all_records(request.user)
    leader_form = ChurchLeaderForm()
    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'add_leader':
            if not full_manage:
                messages.error(request, 'You are not allowed to add leaders.')
                return redirect('core:officer_leaders')
            leader_form = ChurchLeaderForm(request.POST, request.FILES)
            if leader_form.is_valid():
                leader = leader_form.save()
                messages.success(request, f'Leader {leader.full_name} added successfully.')
                return redirect('core:officer_leaders')
        elif action == 'delete_leader':
            if not full_manage:
                messages.error(request, 'You are not allowed to delete leaders.')
                return redirect('core:officer_leaders')
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
        'can_full_manage': full_manage,
    }
    return render(request, 'core/officer_leaders.html', context)


@login_required
@user_passes_test(is_staff_or_admin)
def officer_events(request):
    site_config = get_site_config()
    full_manage = can_manage_all_records(request.user)
    event_form = EventForm()
    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'add_event':
            if not full_manage:
                messages.error(request, 'You are not allowed to add events.')
                return redirect('core:officer_events')
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
            if not full_manage:
                messages.error(request, 'You are not allowed to delete events.')
                return redirect('core:officer_events')
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
        'can_full_manage': full_manage,
    }
    return render(request, 'core/officer_events.html', context)


@login_required
@user_passes_test(is_staff_or_admin)
def officer_messages(request):
    site_config = get_site_config()
    full_manage = can_manage_all_records(request.user)
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
            if not full_manage:
                messages.error(request, 'You are not allowed to delete messages.')
                return redirect('core:officer_messages')
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
        'can_full_manage': full_manage,
    }
    return render(request, 'core/officer_messages.html', context)


@login_required
@user_passes_test(is_staff_or_admin)
def officer_member_edit(request, profile_id):
    if not can_manage_all_records(request.user):
        messages.error(request, 'You are not allowed to edit members.')
        return redirect('core:officer_members')
    site_config = get_site_config()
    profile = get_object_or_404(UserProfile.objects.select_related('user'), id=profile_id)
    form = OfficerMemberCreateForm(
        request.POST or None,
        user_instance=profile.user,
        profile_instance=profile,
        allow_staff_toggle=can_manage_all_records(request.user),
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
    if not can_manage_all_records(request.user):
        messages.error(request, 'You are not allowed to edit zones.')
        return redirect('core:officer_structure')
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
    if not can_manage_all_records(request.user):
        messages.error(request, 'You are not allowed to edit branches.')
        return redirect('core:officer_structure')
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
    if not can_manage_all_records(request.user):
        messages.error(request, 'You are not allowed to edit ministries.')
        return redirect('core:officer_ministries')
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
    if not can_manage_all_records(request.user):
        messages.error(request, 'You are not allowed to edit leaders.')
        return redirect('core:officer_leaders')
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
    if not can_manage_all_records(request.user):
        messages.error(request, 'You are not allowed to edit events.')
        return redirect('core:officer_events')
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
    if not can_manage_all_records(request.user):
        messages.error(request, 'You are not allowed to edit messages in detail.')
        return redirect('core:officer_messages')
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


@login_required
def role_assignment_edit(request, profile_id):
    requester_profile = get_user_profile(request.user)
    if not requester_profile or requester_profile.role not in {'pastor', 'secretary'}:
        messages.error(request, 'You do not have permission to assign roles.')
        return redirect('core:dashboard')
    site_config = get_site_config()
    target_profile = get_object_or_404(UserProfile.objects.select_related('user'), id=profile_id)
    form = UserRoleAssignmentForm(request.POST or None, instance=target_profile)
    if request.method == 'POST' and form.is_valid():
        previous_data = snapshot_instance(target_profile, ['role', 'zone_id', 'deacon_group_id', 'church_branch', 'ministry_role_id', 'tithe_card_number'])
        updated = form.save()
        if updated.role == 'zone_leader' and updated.zone:
            ZoneLeadership.objects.update_or_create(
                user=updated.user,
                zone=updated.zone,
                role='zone_leader',
                defaults={'is_active': True},
            )
        if updated.role == 'deacon_leader' and updated.deacon_group:
            updated.zone = updated.deacon_group.zone
            updated.save(update_fields=['zone'])
            if updated.deacon_group.leader_id != updated.user_id:
                updated.deacon_group.leader = updated.user
                updated.deacon_group.save(update_fields=['leader'])
        create_action_log(
            request.user,
            'roles',
            'update',
            'UserProfile',
            updated.id,
            updated.user.get_full_name() or updated.user.username,
            description='Role assignment updated from dashboard.',
            previous_data=previous_data,
            new_data=snapshot_instance(updated, ['role', 'zone_id', 'deacon_group_id', 'church_branch', 'ministry_role_id', 'tithe_card_number']),
        )
        messages.success(request, f'Role assignment updated for {updated.user.get_full_name() or updated.user.username}.')
        return redirect('core:role_assignment_dashboard')
    context = build_officer_form_context(
        site_config,
        'dashboard',
        'Assign Role & Scope',
        'Mpe role, zone, deacon group, na uwezo wa mfumo ndani ya dashboard.',
        form,
        'core:role_assignment_dashboard',
    )
    return render(request, 'core/officer_form.html', context)


@login_required
def financial_offering_edit(request, offering_id):
    profile = get_user_profile(request.user)
    if not profile or profile.role not in {'secretary', 'accountant', 'zone_leader', 'deacon_leader'}:
        messages.error(request, 'You do not have permission to edit offerings.')
        return redirect('core:dashboard')
    site_config = get_site_config()
    offering = get_object_or_404(OfferingRecord, id=offering_id)
    zone_scope, deacon_scope = get_user_scope(profile, request.user)
    if profile.role in {'zone_leader', 'deacon_leader'} and not filter_contributions_by_scope(OfferingRecord.objects.filter(id=offering.id), zone_scope, deacon_scope).exists():
        messages.error(request, 'You do not have permission to edit this offering.')
        return redirect('core:financial_offerings')
    form = OfferingRecordForm(request.POST or None, instance=offering)
    if request.method == 'POST' and form.is_valid():
        previous_data = snapshot_instance(offering, ['category_id', 'zone_id', 'deacon_group_id', 'amount', 'week_label', 'month', 'year', 'service_date'])
        updated = form.save(commit=False)
        updated.approval_status = get_record_approval_status(request.user)
        updated.save()
        create_action_log(
            request.user,
            'offerings',
            'update',
            'OfferingRecord',
            offering.id,
            offering.category.name,
            description='Offering record updated from dashboard.',
            previous_data=previous_data,
            new_data=snapshot_instance(offering, ['category_id', 'zone_id', 'deacon_group_id', 'amount', 'week_label', 'month', 'year', 'service_date']),
        )
        messages.success(request, 'Offering updated successfully.')
        return redirect('core:financial_offerings')
    context = build_officer_form_context(site_config, 'dashboard', 'Edit Offering', 'Hariri sadaka ya zone, jumapili, ijumaa, au kundi husika.', form, 'core:financial_offerings')
    return render(request, 'core/officer_form.html', context)


@login_required
def financial_contribution_edit(request, contribution_id):
    profile = get_user_profile(request.user)
    if not profile or profile.role not in {'secretary', 'accountant', 'zone_leader', 'deacon_leader'}:
        messages.error(request, 'You do not have permission to edit contributions.')
        return redirect('core:dashboard')
    site_config = get_site_config()
    contribution = get_object_or_404(FundraisingContribution, id=contribution_id)
    zone_scope, deacon_scope = get_user_scope(profile, request.user)
    scoped_contributions = FundraisingContribution.objects.filter(id=contribution.id)
    if zone_scope:
        scoped_contributions = scoped_contributions.filter(Q(zone=zone_scope) | Q(zone__isnull=True))
    if profile.role in {'zone_leader', 'deacon_leader'} and not scoped_contributions.exists():
        messages.error(request, 'You do not have permission to edit this contribution.')
        return redirect('core:financial_contributions')
    form = FundraisingContributionForm(request.POST or None, instance=contribution)
    if request.method == 'POST' and form.is_valid():
        previous_data = snapshot_instance(contribution, ['campaign_id', 'contributor_id', 'zone_id', 'amount', 'contribution_date', 'week_label'])
        updated = form.save(commit=False)
        updated.approval_status = get_record_approval_status(request.user)
        updated.save()
        create_action_log(
            request.user,
            'offerings',
            'update',
            'FundraisingContribution',
            contribution.id,
            contribution.campaign.name,
            description='Contribution record updated from dashboard.',
            previous_data=previous_data,
            new_data=snapshot_instance(contribution, ['campaign_id', 'contributor_id', 'zone_id', 'amount', 'contribution_date', 'week_label']),
        )
        messages.success(request, 'Contribution updated successfully.')
        return redirect('core:financial_contributions')
    context = build_officer_form_context(site_config, 'dashboard', 'Edit Contribution', 'Hariri michango au harambee ya campaign husika.', form, 'core:financial_contributions')
    return render(request, 'core/officer_form.html', context)


@login_required
def asset_edit(request, asset_id):
    profile = get_user_profile(request.user)
    if not profile or profile.role not in {'secretary', 'pastor', 'institution_manager'}:
        messages.error(request, 'You do not have permission to edit assets.')
        return redirect('core:dashboard')
    site_config = get_site_config()
    asset = get_object_or_404(ChurchAsset, id=asset_id)
    form = ChurchAssetForm(request.POST or None, instance=asset)
    if request.method == 'POST' and form.is_valid():
        previous_data = snapshot_instance(asset, ['name', 'category_id', 'serial_number', 'quantity', 'condition', 'location', 'estimated_value', 'status'])
        updated = form.save(commit=False)
        updated.approval_status = get_record_approval_status(request.user)
        updated.save()
        create_action_log(
            request.user,
            'assets',
            'update',
            'ChurchAsset',
            asset.id,
            asset.name,
            description='Church asset updated from dashboard.',
            previous_data=previous_data,
            new_data=snapshot_instance(asset, ['name', 'category_id', 'serial_number', 'quantity', 'condition', 'location', 'estimated_value', 'status']),
        )
        messages.success(request, 'Church asset updated successfully.')
        return redirect('core:asset_management')
    context = build_officer_form_context(site_config, 'dashboard', 'Edit Asset', 'Hariri taarifa za asset ya kanisa.', form, 'core:asset_management')
    return render(request, 'core/officer_form.html', context)


@login_required
def family_member_edit(request, family_id):
    profile = get_user_profile(request.user)
    if not profile:
        messages.error(request, 'Profile is required.')
        return redirect('core:dashboard')
    site_config = get_site_config()
    family = get_object_or_404(FamilyMember, id=family_id, primary_member=profile)
    form = FamilyMemberForm(request.POST or None, instance=family)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Family member updated successfully.')
        return redirect('core:family_management')
    context = build_officer_form_context(site_config, 'dashboard', 'Edit Family Member', 'Hariri taarifa za family member wako.', form, 'core:family_management')
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
        marital_status = request.POST.get('marital_status')
        spouse_name = request.POST.get('spouse_name')
        occupation = request.POST.get('occupation')
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
            marital_status=marital_status,
            spouse_name=spouse_name,
            occupation=occupation,
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
        profile.marital_status = request.POST.get('marital_status')
        profile.spouse_name = request.POST.get('spouse_name')
        profile.occupation = request.POST.get('occupation')
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
    profile = get_user_profile(user)
    is_admin = user.is_staff or user.is_superuser or bool(profile and profile.role in {'secretary', 'accountant', 'zone_leader', 'deacon_leader'})
    zone_scope, deacon_scope = get_user_scope(profile, user)

    site_config = SiteConfig.objects.first()
    if not site_config:
        site_config = SiteConfig.objects.create()
    
    if request.method == 'POST':
        amount = request.POST.get('amount')
        year = request.POST.get('year')
        month = request.POST.get('month')
        payment_method = request.POST.get('payment_method')
        notes = request.POST.get('notes')
        tithe_card_number = request.POST.get('tithe_card_number', '').strip()
        
        # For staff/admin, get selected user from form
        if is_admin:
            selected_user_id = request.POST.get('user_id')
            if tithe_card_number:
                selected_profile = get_object_or_404(UserProfile, tithe_card_number=tithe_card_number)
                tithe_user = selected_profile.user
            elif selected_user_id:
                tithe_user = User.objects.get(id=selected_user_id)
            else:
                tithe_user = user
            if zone_scope and getattr(tithe_user, 'userprofile', None) and tithe_user.userprofile.zone_id != getattr(zone_scope, 'id', None):
                messages.error(request, 'You can only record tithe for members in your assigned zone.')
                return redirect('core:add_tithe')
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
            approval_status=get_record_approval_status(request.user),
            recorded_by=user,  # Track who recorded it
            date_paid=timezone.now()
        )
        tithe.save()
        create_action_log(
            request.user,
            'tithes',
            'create',
            'Tithe',
            tithe.id,
            tithe_user.get_full_name() or tithe_user.username,
            description='Tithe record created from dashboard.',
            new_data=snapshot_instance(tithe, ['user_id', 'amount', 'month', 'year', 'payment_method', 'status', 'date_paid', 'recorded_by_id']),
        )
        
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
        'zone_scope': zone_scope,
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
    profile = get_user_profile(request.user)
    zone_scope, deacon_scope = get_user_scope(profile, request.user)
    users = []
    
    if query:
        users = User.objects.filter(
            Q(username__icontains=query) |
            Q(first_name__icontains=query) |
            Q(last_name__icontains=query) |
            Q(email__icontains=query)
        ).filter(is_active=True)
        if zone_scope:
            users = users.filter(userprofile__zone=zone_scope)
        users = users[:10]
    
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

@login_required
@user_passes_test(is_staff_or_admin)
def search_users_api(request):
    """JSON API for searching users (for AJAX)"""
    query = request.GET.get('q', '')
    
    if len(query) < 2:
        return JsonResponse({'users': []})
    
    profile = get_user_profile(request.user)
    zone_scope, deacon_scope = get_user_scope(profile, request.user)
    users = User.objects.filter(
        Q(username__icontains=query) |
        Q(first_name__icontains=query) |
        Q(last_name__icontains=query) |
        Q(email__icontains=query)
    ).filter(is_active=True)
    if zone_scope:
        users = users.filter(userprofile__zone=zone_scope)
    users = users[:10]
    
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

    profile = get_user_profile(request.user)
    zone_scope, deacon_scope = get_user_scope(profile, request.user)
    tithes = Tithe.objects.select_related('user', 'recorded_by').order_by('-date_paid')
    tithes = filter_tithes_by_scope(tithes, zone_scope, deacon_scope)
    
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
    if zone_scope:
        users = users.filter(userprofile__zone=zone_scope)
    
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
    return render(request, 'core/tithe_receipt.html', context)


@login_required
def offering_receipt(request, offering_id):
    profile = get_user_profile(request.user)
    if not profile or profile.role not in {'secretary', 'accountant', 'zone_leader', 'deacon_leader', 'pastor'}:
        messages.error(request, 'You do not have permission to view offering receipts.')
        return redirect('core:dashboard')
    site_config = get_site_config()
    offering = get_object_or_404(OfferingRecord.objects.select_related('category', 'zone', 'deacon_group', 'recorded_by'), id=offering_id)
    zone_scope, deacon_scope = get_user_scope(profile, request.user)
    scoped = filter_contributions_by_scope(OfferingRecord.objects.filter(id=offering.id), zone_scope, deacon_scope)
    if profile.role in {'zone_leader', 'deacon_leader'} and not scoped.exists():
        messages.error(request, 'You do not have permission to view this offering receipt.')
        return redirect('core:financial_offerings')
    return render(request, 'core/offering_receipt.html', {'offering': offering, 'site_config': site_config})
