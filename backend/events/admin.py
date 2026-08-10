from django.contrib import admin

from .models import City


@admin.register(City)
class CityAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug', 'calendar_id', 'is_default', 'is_active', 'created_at']
    list_filter = ['is_active', 'is_default', 'created_at']
    search_fields = ['name', 'slug', 'calendar_id']
    list_editable = ['is_active']
    # Django's urlify.js carries a Polish map, so the browser fills in the same
    # value City.save() would - see events/slugs.py for why the stroked L needs
    # special handling. The field stays editable: once a city has been shared,
    # its subdomain must survive a rename of the city.
    prepopulated_fields = {'slug': ('name',)}
