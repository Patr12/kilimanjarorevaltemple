from django.contrib import admin
from .models import ChurchBranch, ChurchLeader, UserProfile, Zone

@admin.register(ChurchLeader)
class ChurchLeaderAdmin(admin.ModelAdmin):
    list_display = ('full_name', 'title', 'level', 'order', 'is_active')
    list_filter = ('level', 'is_active')
    search_fields = ('full_name', 'title')


@admin.register(Zone)
class ZoneAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)


@admin.register(ChurchBranch)
class ChurchBranchAdmin(admin.ModelAdmin):
    list_display = ('name', 'zone')
    list_filter = ('zone',)
    search_fields = ('name', 'zone__name')


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'phone', 'church_branch', 'zone', 'ministry_role', 'joined_at')
    list_filter = ('zone', 'ministry_role', 'joined_at')
    search_fields = (
        'user__username',
        'user__first_name',
        'user__last_name',
        'user__email',
        'phone',
        'church_branch',
    )
    autocomplete_fields = ('user', 'zone', 'ministry_role')
