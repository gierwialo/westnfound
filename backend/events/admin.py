from django.contrib import admin
from .models import Calendar


@admin.register(Calendar)
class CalendarAdmin(admin.ModelAdmin):
    list_display = ['name', 'calendar_id', 'is_active', 'created_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['name', 'calendar_id']
    list_editable = ['is_active']
