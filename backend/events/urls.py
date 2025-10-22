from django.urls import path
from .views import NextEventView

urlpatterns = [
    path('next-event/', NextEventView.as_view(), name='next-event'),
]
