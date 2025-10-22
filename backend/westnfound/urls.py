"""
URL configuration for westnfound project.
"""
from django.contrib import admin
from django.urls import path, include
import os

# Get admin URL from environment variable (default: 'admin')
ADMIN_URL = os.environ.get('DJANGO_ADMIN_URL', 'admin').strip('/')

urlpatterns = [
    path(f'{ADMIN_URL}/', admin.site.urls),
    path('api/', include('events.urls')),
]
