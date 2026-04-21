from django.urls import path
from django.contrib.auth import views as auth_views
from . import views
app_name = 'core'
urlpatterns = [
    # Homepage
    path('', views.HomeView.as_view(), name='home'),
    
    # Authentication
    path('login/', auth_views.LoginView.as_view(template_name='core/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    path('register/', auth_views.PasswordChangeView.as_view(template_name='core/register.html'), name='register'),
    
    # Core Pages
    path('about/', views.AboutView.as_view(), name='about'),
    path('contact/', views.ContactView.as_view(), name='contact'),
    path('services/', views.ServiceTimesView.as_view(), name='services'),
    path('gallery/', views.GalleryView.as_view(), name='gallery'),
    
    # Ministries
    path('ministries/', views.MinistriesView.as_view(), name='ministries'),
    path('ministries/<slug:slug>/', views.MinistryDetailView.as_view(), name='ministry_detail'),
    
    # Events
    path('events/', views.EventsView.as_view(), name='events'),
    path('events/<slug:slug>/', views.EventDetailView.as_view(), name='event_detail'),
    path('events/<slug:slug>/register/', views.EventRegisterView.as_view(), name='event_register'),
    
    # Dashboard
    path('dashboard/', views.dashboard, name='dashboard'),
    path('dashboard/officer/', views.officer_dashboard, name='officer_dashboard'),
    path('dashboard/officer/members/', views.officer_members, name='officer_members'),
    path('dashboard/officer/members/<int:profile_id>/edit/', views.officer_member_edit, name='officer_member_edit'),
    path('dashboard/officer/structure/', views.officer_structure, name='officer_structure'),
    path('dashboard/officer/structure/zones/<int:zone_id>/edit/', views.officer_zone_edit, name='officer_zone_edit'),
    path('dashboard/officer/structure/branches/<int:branch_id>/edit/', views.officer_branch_edit, name='officer_branch_edit'),
    path('dashboard/officer/ministries/', views.officer_ministries, name='officer_ministries'),
    path('dashboard/officer/ministries/<int:ministry_id>/edit/', views.officer_ministry_edit, name='officer_ministry_edit'),
    path('dashboard/officer/leaders/', views.officer_leaders, name='officer_leaders'),
    path('dashboard/officer/leaders/<int:leader_id>/edit/', views.officer_leader_edit, name='officer_leader_edit'),
    path('dashboard/officer/events/', views.officer_events, name='officer_events'),
    path('dashboard/officer/events/<int:event_id>/edit/', views.officer_event_edit, name='officer_event_edit'),
    path('dashboard/officer/messages/', views.officer_messages, name='officer_messages'),
    path('dashboard/officer/messages/<int:message_id>/edit/', views.officer_message_edit, name='officer_message_edit'),
    # Profile URLs
    path('profile/', views.profile_view, name='profile'),
    path('profile/create/', views.create_profile, name='create_profile'),
    path('profile/edit/', views.edit_profile, name='edit_profile'),
    
    # Tithe URLs
    path('tithes/', views.tithe_history, name='tithe_history'),
    path('tithes/add/', views.add_tithe, name='add_tithe'),
    path('tithes/<int:tithe_id>/', views.tithe_detail, name='tithe_detail'),
      # Admin/Staff URLs
    path('staff/tithes/', views.admin_tithe_list, name='admin_tithe_list'),
    path('search-users/', views.search_users_api, name='search_users'),
]
