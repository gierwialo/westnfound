"""
URL configuration for westnfound project.
"""
from django.contrib import admin
from django.urls import path, include
import os

from events.seo import RobotsView, SitemapView
from events.views import CalendarFeedView

# Get admin URL from environment variable (default: 'admin')
ADMIN_URL = os.environ.get('DJANGO_ADMIN_URL', 'admin').strip('/')

urlpatterns = [
    path(f'{ADMIN_URL}/', admin.site.urls),
    path('api/', include('events.urls')),
    # The subscribable feed, in both spellings. /kalendarz and /calendar
    # without the extension are the human page, served by nginx from the
    # frontend - they never reach Django.
    path('kalendarz.ics', CalendarFeedView.as_view(), name='calendar-feed-pl'),
    path('calendar.ics', CalendarFeedView.as_view(), name='calendar-feed-en'),
    # Both depend on the Host header - each city names its own sitemap, and
    # the apex is the only one that lists the other cities.
    path('robots.txt', RobotsView.as_view(), name='robots'),
    path('sitemap.xml', SitemapView.as_view(), name='sitemap'),
]
