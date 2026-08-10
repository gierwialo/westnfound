from django.http import JsonResponse
from django.views import View
from .models import City
from .services import GoogleCalendarService
import logging

logger = logging.getLogger(__name__)


class NextEventView(View):
    """API endpoint to get the next upcoming event from all active calendars"""

    def get(self, request):
        try:
            # Step 5.2 will narrow this to the city resolved from the Host
            # header; until then every active city is merged, which is what
            # this endpoint has always done.
            active_cities = City.objects.filter(is_active=True)

            if not active_cities.exists():
                return JsonResponse({
                    'error': 'No active cities',
                    'message': 'Add cities in the admin panel'
                }, status=404)

            calendar_ids = [city.calendar_id for city in active_cities]

            # Fetch next event
            service = GoogleCalendarService()
            event = service.get_next_event_from_multiple_calendars(calendar_ids)

            if not event:
                return JsonResponse({
                    'error': 'No upcoming events',
                    'message': 'No upcoming events found in calendars'
                }, status=404)

            return JsonResponse({
                'success': True,
                'event': event
            })

        except Exception as e:
            logger.error(f"Error in NextEventView: {str(e)}")
            return JsonResponse({
                'error': 'Server error',
                'message': str(e)
            }, status=500)


class NextEventsView(View):
    """API endpoint to get the next N upcoming events from all active calendars"""

    def get(self, request):
        try:
            # Step 5.2 will narrow this to the city resolved from the Host
            # header; until then every active city is merged, which is what
            # this endpoint has always done.
            active_cities = City.objects.filter(is_active=True)

            if not active_cities.exists():
                return JsonResponse({
                    'error': 'No active cities',
                    'message': 'Add cities in the admin panel'
                }, status=404)

            # Get limit parameter from query string (default: 3)
            try:
                limit = int(request.GET.get('limit', 3))
                if limit < 1 or limit > 10:
                    limit = 3
            except ValueError:
                limit = 3

            calendar_ids = [city.calendar_id for city in active_cities]

            # Fetch next events
            service = GoogleCalendarService()
            events = service.get_next_events_from_multiple_calendars(calendar_ids, limit)

            if not events:
                return JsonResponse({
                    'error': 'No upcoming events',
                    'message': 'No upcoming events found in calendars'
                }, status=404)

            return JsonResponse({
                'success': True,
                'events': events,
                'count': len(events)
            })

        except Exception as e:
            logger.error(f"Error in NextEventsView: {str(e)}")
            return JsonResponse({
                'error': 'Server error',
                'message': str(e)
            }, status=500)
