from django.http import JsonResponse
from django.views import View
from .services import GoogleCalendarService
import logging

logger = logging.getLogger(__name__)


def _no_city_response(request):
    """The shared 404 for "this host names no city we serve".

    ``request.city`` is set by CityMiddleware from the Host header. It is None
    either because the subdomain names a city we do not have, or because no
    city is configured at all - worth telling apart in the message, since only
    the second one is something the owner can fix in the admin panel.
    """
    if getattr(request, 'city_is_unknown', False):
        return JsonResponse({
            'error': 'Unknown city',
            'message': f'No city is served at {request.get_host()}'
        }, status=404)
    return JsonResponse({
        'error': 'No active cities',
        'message': 'Add cities in the admin panel'
    }, status=404)


class NextEventView(View):
    """API endpoint to get the next upcoming event for the request's city"""

    def get(self, request):
        try:
            city = getattr(request, 'city', None)
            if city is None:
                return _no_city_response(request)

            service = GoogleCalendarService()
            event = service.get_next_event_from_multiple_calendars([city.calendar_id])

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
    """API endpoint to get the next N upcoming events for the request's city"""

    def get(self, request):
        try:
            city = getattr(request, 'city', None)
            if city is None:
                return _no_city_response(request)

            # Get limit parameter from query string (default: 3)
            try:
                limit = int(request.GET.get('limit', 3))
                if limit < 1 or limit > 10:
                    limit = 3
            except ValueError:
                limit = 3

            service = GoogleCalendarService()
            events = service.get_next_events_from_multiple_calendars(
                [city.calendar_id], limit
            )

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
