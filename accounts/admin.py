from django.contrib import admin
from .models import ChurchLeader

@admin.register(ChurchLeader)
class ChurchLeaderAdmin(admin.ModelAdmin):
    list_display = ('full_name', 'title', 'level', 'order', 'is_active')
    list_filter = ('level', 'is_active')
    search_fields = ('full_name', 'title')
