from concurrent.futures import ThreadPoolExecutor
from urllib.parse import quote

from django.http import HttpResponse, HttpResponseNotFound, JsonResponse
from django.views import View
from .services import CalendarFeedService, GoogleCalendarService
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


# Every city we serve is in Poland; kept as it was in the nginx config that
# first hardcoded Warsaw's calendar into a redirect.
DISPLAY_TIMEZONE = 'Europe/Warsaw'


def _google_embed_url(city):
    """Google's own page for this calendar, still worth linking to.

    safe='' matters: quote() leaves "/" alone by default, and this address has
    carried the timezone as Europe%2FWarsaw since it lived in nginx.
    """
    return (
        'https://calendar.google.com/calendar/embed'
        f'?src={quote(city.calendar_id, safe="")}'
        f'&ctz={quote(DISPLAY_TIMEZONE, safe="")}'
    )


class CalendarFeedView(View):
    """The city's calendar as an iCal feed: /kalendarz.ics and /calendar.ics.

    These paths used to redirect a visitor to Google. Serving the calendar
    ourselves makes the address people subscribe to ours, which is what lets
    the calendar behind a city change without every subscriber having to
    resubscribe - and lets bootstrap.json name gdzienawesta.com rather than a
    Google calendar id.

    The caching, and the promise it keeps, live in CalendarFeedService.
    """

    def get(self, request):
        city = getattr(request, 'city', None)
        if city is None:
            return HttpResponseNotFound('No city is served at this address\n')

        service = CalendarFeedService()
        feed, is_stale = service.get(city.calendar_id)
        if feed is None:
            # No copy at all, fresh or stale. Saying so beats answering with
            # an empty calendar, which a subscriber's app would take as "every
            # event was cancelled" and act on.
            return HttpResponse(
                'Calendar temporarily unavailable\n',
                status=502,
                content_type='text/plain; charset=utf-8',
            )

        response = HttpResponse(feed, content_type='text/calendar; charset=utf-8')
        # inline, not attachment: a browser that follows this link should be
        # able to hand it straight to the calendar app.
        response['Content-Disposition'] = f'inline; filename="{city.slug}.ics"'
        response['Cache-Control'] = f'public, max-age={CalendarFeedService.FRESH_SECONDS}'
        if is_stale:
            # Invisible to subscribers, but it turns "did the feed update?"
            # into something a single curl can answer.
            response['X-Feed-Stale'] = '1'
        fetched_at = service.fetched_at(city.calendar_id)
        if fetched_at is not None:
            # For the status page: when this copy left Google, in UTC. Not
            # Last-Modified, which would invite conditional requests from
            # calendar apps and answer them with a time that is ours, not
            # the calendar's.
            response['X-Feed-Fetched'] = fetched_at.strftime('%Y-%m-%dT%H:%M:%SZ')
        return response


def _feed_url(request, city):
    """The address to hand out for subscribing to this city's calendar.

    Deliberately the city's own subdomain, even when the visitor is standing
    on the apex. The default city answers at both, and the page used to build
    this address from wherever the reader happened to be - so everyone who
    subscribed from the front page bound themselves to gdzienawesta.com rather
    than to Warsaw. A subscription is set once and never revisited, so that
    binding outlives any decision to give the apex a different meaning.

    Existing subscriptions are left alone: the apex feed keeps working. This
    only changes what new subscribers are given.

    One spelling, not two. /calendar.ics answers the same, but a feed is not
    read by a person and two addresses for one calendar is a distinction with
    nothing behind it.
    """
    from django.conf import settings

    from .middleware import base_domain_for, scheme_for

    base = (
        base_domain_for(request.get_host(), settings.CITY_BASE_DOMAINS)
        or settings.CITY_BASE_DOMAINS[0]
    )
    host = f'{city.slug}.{base}'
    return f'{scheme_for(host)}://{host}/kalendarz.ics'


class CalendarInfoView(View):
    """What the calendar page needs to know about the city it is showing."""

    def get(self, request):
        city = getattr(request, 'city', None)
        if city is None:
            return _no_city_response(request)

        return JsonResponse({
            'success': True,
            'city': {'name': city.name, 'slug': city.slug},
            'calendar_id': city.calendar_id,
            'timezone': DISPLAY_TIMEZONE,
            'google_url': _google_embed_url(city),
            'feed_url': _feed_url(request, city),
        })


class CitiesView(View):
    """The cities we serve, for the map, the footer and the unknown-city page."""

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
            # Every city on its own subdomain, the default one too: the apex
            # is the map now, not Warsaw. Links are protocol-relative on
            # purpose: Cloudflare terminates TLS, so the origin always sees
            # plain http and would otherwise hand out http:// links on an
            # https page.
            cities.append({
                'name': city.name,
                'slug': city.slug,
                'url': f'//{city.slug}.{base}',
                'latitude': city.latitude,
                'longitude': city.longitude,
                'is_current': current is not None and city.pk == current.pk,
            })

        return JsonResponse({
            'success': True,
            'cities': cities,
            'count': len(cities),
            'current': current.slug if current else None,
        })


class CitiesNextView(View):
    """The next event of every city, for the second line of the map's list.

    Separate from /api/cities/ because it is the slow half: the names can be
    on the page at once, and this fills in behind them. It answers the same on
    every host, because the list it feeds is the same everywhere.
    """

    def get(self, request):
        from .models import City

        cities = list(City.objects.filter(is_active=True))

        # In parallel, because with a cold cache each calendar is a request to
        # Google of up to ten seconds, and there are ten of them. With a warm
        # one the threads only parse. get_next_event() never touches the
        # database, so the workers need no connection of their own.
        service = GoogleCalendarService()
        with ThreadPoolExecutor(max_workers=max(len(cities), 1)) as pool:
            events = list(pool.map(
                lambda city: service.get_next_event(city.calendar_id), cities
            ))

        return JsonResponse({
            'success': True,
            'count': len(cities),
            # A city without an upcoming event, or whose calendar did not
            # answer, gets null: the list shows it without a second line.
            'cities': [
                {
                    'slug': city.slug,
                    'event': event and {
                        'title': event['title'],
                        'start': event['start'],
                        'end': event['end'],
                    },
                }
                for city, event in zip(cities, events)
            ],
        })
