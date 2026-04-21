from django.shortcuts import render, redirect
from django.contrib.auth import login, logout
from django.contrib.auth.forms import AuthenticationForm
from core.models import SiteConfig
from .forms import SignupForm
from core.mixins import SiteConfigMixin
# Create your views here.

def signup_view(request):
     # Get site configuration
    site_config = SiteConfig.objects.first()
    if not site_config:
            site_config = SiteConfig.objects.create()
    if request.method == 'POST':
        form = SignupForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('core:dashboard')
    else:
        
        form = SignupForm()

    return render(request, 'accounts/signup.html', {
         'form': form,
        'site_config': site_config})
    

def login_view(request):
     # Get site configuration
    site_config = SiteConfig.objects.first()
    if not site_config:
            site_config = SiteConfig.objects.create()

    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            login(request, form.get_user())
            return redirect('core:dashboard')
    else:
         form = AuthenticationForm()

    return render(request, 'accounts/login.html', {'form': form, 'site_config': site_config})  

def logout_view(request):
    logout(request)
    return redirect('core:home')      
