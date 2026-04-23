from django.contrib import admin
from .models import ChurchBranch, ChurchLeader, DeaconGroup, FamilyMember, UserProfile, Zone, ZoneLeadership

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
    list_display = ('user', 'role', 'phone', 'church_branch', 'zone', 'deacon_group', 'ministry_role', 'joined_at')
    list_filter = ('role', 'zone', 'deacon_group', 'ministry_role', 'joined_at')
    search_fields = (
        'user__username',
        'user__first_name',
        'user__last_name',
        'user__email',
        'phone',
        'church_branch',
    )
    autocomplete_fields = ('user', 'zone', 'ministry_role')


@admin.register(ZoneLeadership)
class ZoneLeadershipAdmin(admin.ModelAdmin):
    list_display = ('user', 'zone', 'role', 'is_active', 'appointed_on')
    list_filter = ('role', 'is_active', 'zone')
    autocomplete_fields = ('user', 'zone')


@admin.register(DeaconGroup)
class DeaconGroupAdmin(admin.ModelAdmin):
    list_display = ('name', 'zone', 'leader', 'is_active')
    list_filter = ('zone', 'is_active')
    search_fields = ('name', 'zone__name', 'leader__username', 'leader__first_name', 'leader__last_name')
    autocomplete_fields = ('zone', 'leader')


@admin.register(FamilyMember)
class FamilyMemberAdmin(admin.ModelAdmin):
    list_display = ('full_name', 'primary_member', 'relationship', 'is_member_account', 'created_at')
    list_filter = ('relationship', 'is_member_account')
    search_fields = ('full_name', 'primary_member__user__username', 'primary_member__user__first_name', 'primary_member__user__last_name')
    autocomplete_fields = ('primary_member',)
