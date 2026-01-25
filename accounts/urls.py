from django.urls import path
from . import views
from django.views.generic import TemplateView

app_name = 'accounts'
# accounts/urls.py
urlpatterns = [
    path('signup/', views.signup_view, name='signup'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),

      # New URLs for Terms and Privacy
    path('terms/', TemplateView.as_view(template_name='accounts/terms.html'), name='terms'),
    path('privacy/', TemplateView.as_view(template_name='accounts/privacy.html'), name='privacy'),
]