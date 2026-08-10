"""
URL configuration for westnfound project.
"""
from django.contrib import admin
from django.urls import path, include
import os

from events.views import CalendarRedirectView

# Get admin URL from environment variable (default: 'admin')
ADMIN_URL = os.environ.get('DJANGO_ADMIN_URL', 'admin').strip('/')

urlpatterns = [
    path(f'{ADMIN_URL}/', admin.site.urls),
    path('api/', include('events.urls')),
    # Both spellings, with and without the trailing slash, so no visitor gets
    # bounced through a redirect on the way to a redirect.
    path('kalendarz', CalendarRedirectView.as_view(), name='calendar-redirect-pl'),
    path('kalendarz/', CalendarRedirectView.as_view()),
    path('calendar', CalendarRedirectView.as_view(), name='calendar-redirect-en'),
    path('calendar/', CalendarRedirectView.as_view()),
]
