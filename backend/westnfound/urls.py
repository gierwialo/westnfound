"""
URL configuration for westnfound project.
"""
from django.contrib import admin
from django.urls import path, include
import os

from events.documents import CalendarPageView, HomeView
from events.seo import RobotsView, SitemapView
from events.views import CalendarFeedView

# Get admin URL from environment variable (default: 'admin')
ADMIN_URL = os.environ.get('DJANGO_ADMIN_URL', 'admin').strip('/')

urlpatterns = [
    path(f'{ADMIN_URL}/', admin.site.urls),
    path('api/', include('events.urls')),
    # The subscribable feed, in both spellings.
    path('kalendarz.ics', CalendarFeedView.as_view(), name='calendar-feed-pl'),
    path('calendar.ics', CalendarFeedView.as_view(), name='calendar-feed-en'),
    # The pages a person reads. nginx still holds the file; Django hands it
    # over with the title and description of the city in the Host header,
    # which is the only thing on these pages that a crawler can see without
    # running our JavaScript.
    path('', HomeView.as_view(), name='home'),
    path('index.html', HomeView.as_view(), name='home-file'),
    path('kalendarz', CalendarPageView.as_view(), name='calendar-page-pl'),
    path('kalendarz/', CalendarPageView.as_view(), name='calendar-page-pl-slash'),
    path('calendar', CalendarPageView.as_view(), name='calendar-page-en'),
    path('calendar/', CalendarPageView.as_view(), name='calendar-page-en-slash'),
    # Both depend on the Host header - each city names its own sitemap, and
    # the apex is the only one that lists the other cities.
    path('robots.txt', RobotsView.as_view(), name='robots'),
    path('sitemap.xml', SitemapView.as_view(), name='sitemap'),
]
