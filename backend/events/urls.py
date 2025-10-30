from django.urls import path
from .views import NextEventView, NextEventsView

urlpatterns = [
    path('next-event/', NextEventView.as_view(), name='next-event'),
    path('next-events/', NextEventsView.as_view(), name='next-events'),
]
