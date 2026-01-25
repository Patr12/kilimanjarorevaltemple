# core/mixins.py
from django.shortcuts import get_object_or_404
from .models import SiteConfig

class SiteConfigMixin:
    """Mixin to add site configuration to context"""
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        site_config = SiteConfig.objects.first()
        if not site_config:
            site_config = SiteConfig.objects.create()
        context['site_config'] = site_config
        return context