from django.contrib import admin
from django.contrib.auth.models import User
from .models import *


# Register models here
@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = ['name', 
                    'description',
                    'output', 
                    'status', 
                    'assignee', 
                    'owner',
                    'is_submitted',
                    'is_approved',
                    'is_active',
                    'created_on',
                    'updated_on',
                    'submitted_on',
                    'approved_on'
                ]
    
    search_fields = ['name', 'owner__username', 'assignee__username']
    list_filter = ['status', 'is_active']
    ordering = ['name', 'created_on']
    readonly_fields = ['status', 'is_active', 'created_on', 'updated_on', 'submitted_on', 'approved_on']

# TODO we might want to use a customized user model in the future

# customize the admin interface for User model
admin.site.unregister(User)

class UserAdmin(admin.ModelAdmin):
    list_display = ['username', 'email', 'first_name', 'last_name']
    search_fields = ['username', 'email', 'first_name', 'last_name']
    ordering = ['username']

admin.site.register(User, UserAdmin)

@admin.register(Property)
class PropertyAdmin(admin.ModelAdmin):
    list_display = ['name', 'creator']


@admin.register(TaskProperty)
class TaskPropertyAdmin(admin.ModelAdmin):
    list_display = ['task', 'property']
    search_fields = ['task__name', 'property__name']


@admin.register(UserProperty)
class UserPropertyAdmin(admin.ModelAdmin):
    list_display = ['user', 'property', 'is_interested']
    search_fields = ['user__username', 'property__name']
    list_filter = ['is_interested']


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'is_employer']
    search_fields = ['user__username']
    list_filter = ['is_employer']
