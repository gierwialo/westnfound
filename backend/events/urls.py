from django.urls import path
from .views import (
    CalendarInfoView,
    CitiesNextView,
    CitiesView,
    NextEventView,
    NextEventsView,
)

urlpatterns = [
    path('next-event/', NextEventView.as_view(), name='next-event'),
    path('next-events/', NextEventsView.as_view(), name='next-events'),
    path('cities/', CitiesView.as_view(), name='cities'),
    path('cities/next/', CitiesNextView.as_view(), name='cities-next'),
    path('calendar/', CalendarInfoView.as_view(), name='calendar-info'),
]
