from urllib.parse import quote

from django.http import HttpResponseNotFound, HttpResponseRedirect, JsonResponse
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


class CalendarRedirectView(View):
    """Send /kalendarz and /calendar to the city's Google Calendar.

    These four paths used to be `return 302` blocks in nginx.prod.conf with
    Warsaw's calendar written into them. They live here now so that adding a
    city in the admin panel gives it a working calendar address too, instead
    of a page that works and a link that does not.
    """

    # Every city we serve is in Poland; kept as it was in the nginx config.
    DISPLAY_TIMEZONE = 'Europe/Warsaw'

    def get(self, request):
        city = getattr(request, 'city', None)
        if city is None:
            # Step 5.4 replaces this with the page listing the cities we do
            # serve; a bare response keeps the shape right until then.
            return HttpResponseNotFound('No city is served at this address\n')

        # safe='' matters: quote() leaves "/" alone by default, and the target
        # nginx used carried the timezone as Europe%2FWarsaw.
        return HttpResponseRedirect(
            'https://calendar.google.com/calendar/embed'
            f'?src={quote(city.calendar_id, safe="")}'
            f'&ctz={quote(self.DISPLAY_TIMEZONE, safe="")}'
        )


class CitiesView(View):
    """The cities we serve, for the footer and the unknown-city page."""

    def get(self, request):
        from django.conf import settings

        from .middleware import base_domain_for
        from .models import City

        base = (
            base_domain_for(request.get_host(), settings.CITY_BASE_DOMAINS)
            or settings.CITY_BASE_DOMAINS[0]
        )
        current = getattr(request, 'city', None)

        cities = []
        for city in City.objects.filter(is_active=True):
            # The default city keeps the apex as its address; the rest live on
            # their own subdomain. Links are protocol-relative on purpose:
            # Cloudflare terminates TLS, so the origin always sees plain http
            # and would otherwise hand out http:// links on an https page.
            host = base if city.is_default else f'{city.slug}.{base}'
            cities.append({
                'name': city.name,
                'slug': city.slug,
                'url': f'//{host}',
                'is_current': current is not None and city.pk == current.pk,
            })

        return JsonResponse({
            'success': True,
            'cities': cities,
            'count': len(cities),
            'current': current.slug if current else None,
        })
