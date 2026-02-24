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