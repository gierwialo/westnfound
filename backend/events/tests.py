from unittest.mock import Mock, patch

from datetime import timedelta

import requests
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.test import TestCase, override_settings
from django.utils import timezone

from .middleware import resolve_city
from .models import City
from .services import GoogleCalendarService
from .slugs import to_slug


class SlugTests(TestCase):
    def test_polish_city_names(self):
        cases = {
            'Warszawa': 'warszawa',
            'Kraków': 'krakow',
            'Gdańsk': 'gdansk',
            'Poznań': 'poznan',
            'Świnoujście': 'swinoujscie',
            'Częstochowa': 'czestochowa',
            'Zielona Góra': 'zielona-gora',
            'Bielsko-Biała': 'bielsko-biala',
        }
        for name, expected in cases.items():
            self.assertEqual(to_slug(name), expected, name)

    def test_stroked_l_is_not_dropped(self):
        """django.utils.text.slugify gives 'odz' and 'wrocaw' here."""
        self.assertEqual(to_slug('Łódź'), 'lodz')
        self.assertEqual(to_slug('Wrocław'), 'wroclaw')

    def test_slug_is_a_valid_dns_label(self):
        for name in ['Zielona Góra', '  Łódź  ', 'Miasto (nowe)', 'Świnoujście!']:
            slug = to_slug(name)
            self.assertRegex(slug, r'^[a-z0-9]([a-z0-9-]*[a-z0-9])?$', name)
            self.assertLessEqual(len(slug), 63)


class CityTests(TestCase):
    def test_slug_filled_in_from_name(self):
        city = City.objects.create(name='Łódź', calendar_id='lodz@example.com')
        self.assertEqual(city.slug, 'lodz')

    def test_explicit_slug_survives_a_rename(self):
        """A shared subdomain must not change when the city is renamed."""
        city = City.objects.create(
            name='Łódź', slug='lodz', calendar_id='lodz@example.com'
        )
        city.name = 'Łódź i okolice'
        city.save()
        self.assertEqual(city.slug, 'lodz')

    def test_only_one_default_city(self):
        warsaw = City.objects.create(
            name='Warszawa', calendar_id='w@example.com', is_default=True
        )
        lodz = City.objects.create(
            name='Łódź', calendar_id='l@example.com', is_default=True
        )
        warsaw.refresh_from_db()
        self.assertFalse(warsaw.is_default)
        self.assertTrue(lodz.is_default)
        self.assertEqual(City.objects.filter(is_default=True).count(), 1)

    def test_default_returns_the_apex_city(self):
        City.objects.create(name='Łódź', calendar_id='l@example.com')
        warsaw = City.objects.create(
            name='Warszawa', calendar_id='w@example.com', is_default=True
        )
        self.assertEqual(City.default(), warsaw)

    def test_default_city_cannot_be_inactive(self):
        city = City(
            name='Warszawa', calendar_id='w@example.com',
            is_default=True, is_active=False,
        )
        with self.assertRaises(ValidationError):
            city.full_clean()

    def test_cities_are_ordered_alphabetically_in_polish(self):
        """Ordering by name would put Łódź last: stroked L sorts after Z."""
        for name in ['Warszawa', 'Łódź', 'Kraków', 'Zielona Góra', 'Gdańsk']:
            City.objects.create(name=name, calendar_id=f'{to_slug(name)}@example.com')
        self.assertEqual(
            [c.name for c in City.objects.all()],
            ['Gdańsk', 'Kraków', 'Łódź', 'Warszawa', 'Zielona Góra'],
        )


class CityResolutionTests(TestCase):
    """Which city a Host header resolves to - see events/middleware.py."""

    BASES = ['gdzienawesta.com', 'lvh.me']

    def setUp(self):
        self.warsaw = City.objects.create(
            name='Warszawa', calendar_id='w@example.com', is_default=True
        )
        self.lodz = City.objects.create(name='Łódź', calendar_id='l@example.com')

    def resolve(self, host):
        return resolve_city(host, self.BASES)

    def test_apex_and_www_give_the_default_city(self):
        for host in ['gdzienawesta.com', 'www.gdzienawesta.com', 'GdzieNaWesta.com']:
            self.assertEqual(self.resolve(host), (self.warsaw, False), host)

    def test_subdomain_gives_its_city(self):
        self.assertEqual(self.resolve('lodz.gdzienawesta.com'), (self.lodz, False))

    def test_unknown_subdomain_is_flagged(self):
        self.assertEqual(self.resolve('krakow.gdzienawesta.com'), (None, True))

    def test_inactive_city_is_not_served(self):
        self.lodz.is_active = False
        self.lodz.save()
        self.assertEqual(self.resolve('lodz.gdzienawesta.com'), (None, True))

    def test_port_and_trailing_dot_are_ignored(self):
        self.assertEqual(self.resolve('lodz.lvh.me:8000'), (self.lodz, False))
        self.assertEqual(self.resolve('lodz.gdzienawesta.com.'), (self.lodz, False))

    def test_deeper_names_are_not_cities(self):
        self.assertEqual(self.resolve('a.lodz.gdzienawesta.com'), (None, True))

    def test_unrecognised_host_falls_back_to_the_default_city(self):
        """A direct hit on the server or a health check must behave as before."""
        for host in ['localhost:8000', '[::1]:8000', '10.0.0.1', 'example.org']:
            self.assertEqual(self.resolve(host), (self.warsaw, False), host)

    def test_local_development_domain(self):
        self.assertEqual(self.resolve('lodz.lvh.me'), (self.lodz, False))
        self.assertEqual(self.resolve('lvh.me'), (self.warsaw, False))


class ApiScopingTests(TestCase):
    """The apex must keep returning what it returned before cities existed."""

    def setUp(self):
        self.warsaw = City.objects.create(
            name='Warszawa', calendar_id='w@example.com', is_default=True
        )
        self.lodz = City.objects.create(name='Łódź', calendar_id='l@example.com')

    def _calendars_asked_for(self, host):
        seen = []

        def fake(_service, calendar_ids, limit=3):
            seen.append(list(calendar_ids))
            return [{'title': 'x', 'start': '2026-09-05T21:00:00+02:00'}]

        with patch.object(
            GoogleCalendarService, 'get_next_events_from_multiple_calendars', fake
        ):
            response = self.client.get('/api/next-events/', HTTP_HOST=host)
        return response, seen

    def test_apex_asks_only_for_the_default_city(self):
        response, seen = self._calendars_asked_for('gdzienawesta.com')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(seen, [['w@example.com']])

    def test_subdomain_asks_only_for_its_own_city(self):
        response, seen = self._calendars_asked_for('lodz.gdzienawesta.com')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(seen, [['l@example.com']])

    def test_unknown_city_is_a_404(self):
        response = self.client.get(
            '/api/next-events/', HTTP_HOST='krakow.gdzienawesta.com'
        )
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()['error'], 'Unknown city')

    def test_empty_database_is_a_different_404(self):
        City.objects.all().delete()
        response = self.client.get('/api/next-events/', HTTP_HOST='gdzienawesta.com')
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()['error'], 'No active cities')


# A real enough calendar: the event endpoints parse this too, so it needs a
# date, and one inside the year ahead that those endpoints look at.
_START = timezone.now() + timedelta(days=30)
ICS = (
    'BEGIN:VCALENDAR\r\nVERSION:2.0\r\nPRODID:-//Test//EN\r\n'
    'BEGIN:VEVENT\r\nUID:praktis-1\r\nDTSTAMP:20260101T000000Z\r\n'
    f'DTSTART:{_START.strftime("%Y%m%dT%H%M%SZ")}\r\n'
    f'DTEND:{(_START + timedelta(hours=3)).strftime("%Y%m%dT%H%M%SZ")}\r\n'
    'SUMMARY:Praktis\r\nEND:VEVENT\r\nEND:VCALENDAR\r\n'
).encode()


def _google_says(body=ICS, status=200):
    response = Mock()
    response.status_code = status
    response.content = body
    return response


@override_settings(CACHES={'default': {'BACKEND': 'django.core.cache.backends.locmem.LocMemCache'}})
class CalendarFeedTests(TestCase):
    """The feed people subscribe to. These paths used to redirect to Google."""

    PATHS = ['/kalendarz.ics', '/calendar.ics']

    def setUp(self):
        cache.clear()
        self.warsaw = City.objects.create(
            name='Warszawa',
            calendar_id='warsawwestiesdance@gmail.com',
            is_default=True,
        )
        self.lodz = City.objects.create(name='Łódź', calendar_id='lodz@example.com')

    def test_apex_serves_the_default_city_calendar(self):
        for path in self.PATHS:
            cache.clear()
            with patch('events.services.requests.get', return_value=_google_says()) as get:
                response = self.client.get(path, HTTP_HOST='gdzienawesta.com')
            self.assertEqual(response.status_code, 200, path)
            self.assertEqual(response.content, ICS, path)
            self.assertEqual(
                response['Content-Type'], 'text/calendar; charset=utf-8', path
            )
            self.assertIn('warsawwestiesdance%40gmail.com', get.call_args[0][0], path)

    def test_subdomain_serves_its_own_calendar(self):
        with patch('events.services.requests.get', return_value=_google_says()) as get:
            response = self.client.get('/kalendarz.ics', HTTP_HOST='lodz.gdzienawesta.com')
        self.assertEqual(response.status_code, 200)
        self.assertIn('lodz%40example.com', get.call_args[0][0])
        self.assertIn('lodz.ics', response['Content-Disposition'])

    def test_unknown_city_gets_a_404(self):
        for path in self.PATHS:
            response = self.client.get(path, HTTP_HOST='krakow.gdzienawesta.com')
            self.assertEqual(response.status_code, 404, path)

    def test_subscribers_share_one_fetch(self):
        """Every subscribed calendar app polls on its own; Google sees one."""
        with patch('events.services.requests.get', return_value=_google_says()) as get:
            for _ in range(5):
                self.client.get('/kalendarz.ics', HTTP_HOST='gdzienawesta.com')
        self.assertEqual(get.call_count, 1)

    def test_the_site_and_the_feed_share_one_fetch(self):
        """The page used to go to Google on every single visit."""
        with patch('events.services.requests.get', return_value=_google_says()) as get:
            events = self.client.get('/api/next-events/', HTTP_HOST='gdzienawesta.com')
            feed = self.client.get('/kalendarz.ics', HTTP_HOST='gdzienawesta.com')

        self.assertEqual(get.call_count, 1)
        self.assertEqual(events.status_code, 200)
        self.assertEqual(events.json()['events'][0]['title'], 'Praktis')
        self.assertEqual(feed.content, ICS)

    def test_each_city_is_cached_separately(self):
        with patch('events.services.requests.get', return_value=_google_says()) as get:
            self.client.get('/kalendarz.ics', HTTP_HOST='gdzienawesta.com')
            self.client.get('/kalendarz.ics', HTTP_HOST='lodz.gdzienawesta.com')
        self.assertEqual(get.call_count, 2)

    def test_last_good_copy_answers_when_google_is_down(self):
        with patch('events.services.requests.get', return_value=_google_says()):
            self.client.get('/kalendarz.ics', HTTP_HOST='gdzienawesta.com')

        cache.delete('ics:fresh:warsawwestiesdance@gmail.com')
        with patch('events.services.requests.get', side_effect=requests.Timeout()):
            response = self.client.get('/kalendarz.ics', HTTP_HOST='gdzienawesta.com')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, ICS)
        self.assertEqual(response['X-Feed-Stale'], '1')

    def test_no_copy_at_all_is_an_error_not_an_empty_calendar(self):
        """An empty calendar reads as "everything was cancelled" to a subscriber."""
        with patch('events.services.requests.get', side_effect=requests.Timeout()):
            response = self.client.get('/kalendarz.ics', HTTP_HOST='gdzienawesta.com')
        self.assertEqual(response.status_code, 502)

    def test_a_login_page_is_neither_served_nor_cached(self):
        """A calendar Google stopped publishing answers 200 with HTML."""
        with patch('events.services.requests.get', return_value=_google_says(b'<html>Sign in')):
            response = self.client.get('/kalendarz.ics', HTTP_HOST='gdzienawesta.com')
        self.assertEqual(response.status_code, 502)

        with patch('events.services.requests.get', return_value=_google_says()):
            response = self.client.get('/kalendarz.ics', HTTP_HOST='gdzienawesta.com')
        self.assertEqual(response.content, ICS)


class CalendarInfoTests(TestCase):
    """Feeds the calendar page: which city, which calendar, where Google is."""

    def setUp(self):
        self.warsaw = City.objects.create(
            name='Warszawa',
            calendar_id='warsawwestiesdance@gmail.com',
            is_default=True,
        )
        self.lodz = City.objects.create(name='Łódź', calendar_id='lodz@example.com')

    def test_google_link_is_what_the_redirect_used_to_point_at(self):
        """Byte for byte the address nginx, and then Django, redirected to."""
        data = self.client.get('/api/calendar/', HTTP_HOST='gdzienawesta.com').json()
        self.assertEqual(
            data['google_url'],
            'https://calendar.google.com/calendar/embed'
            '?src=warsawwestiesdance%40gmail.com&ctz=Europe%2FWarsaw',
        )
        self.assertEqual(data['city']['name'], 'Warszawa')

    def test_subdomain_describes_its_own_city(self):
        data = self.client.get('/api/calendar/', HTTP_HOST='lodz.gdzienawesta.com').json()
        self.assertEqual(data['city']['slug'], 'lodz')
        self.assertEqual(data['calendar_id'], 'lodz@example.com')

    def test_unknown_city_gets_the_shared_404(self):
        response = self.client.get('/api/calendar/', HTTP_HOST='krakow.gdzienawesta.com')
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()['error'], 'Unknown city')


class CitiesEndpointTests(TestCase):
    """Feeds the footer and the unknown-city page."""

    def setUp(self):
        self.warsaw = City.objects.create(
            name='Warszawa', calendar_id='w@example.com', is_default=True
        )
        self.lodz = City.objects.create(name='Łódź', calendar_id='l@example.com')

    def get(self, host='gdzienawesta.com'):
        return self.client.get('/api/cities/', HTTP_HOST=host).json()

    def test_default_city_links_to_the_apex(self):
        by_slug = {c['slug']: c for c in self.get()['cities']}
        self.assertEqual(by_slug['warszawa']['url'], '//gdzienawesta.com')
        self.assertEqual(by_slug['lodz']['url'], '//lodz.gdzienawesta.com')

    def test_links_stay_on_the_domain_the_visitor_is_using(self):
        """Working on lvh.me must not produce links out to production."""
        by_slug = {c['slug']: c for c in self.get(host='lodz.lvh.me')['cities']}
        self.assertEqual(by_slug['lodz']['url'], '//lodz.lvh.me')
        self.assertEqual(by_slug['warszawa']['url'], '//lvh.me')

    def test_current_city_is_marked(self):
        data = self.get(host='lodz.gdzienawesta.com')
        self.assertEqual(data['current'], 'lodz')
        current = [c['slug'] for c in data['cities'] if c['is_current']]
        self.assertEqual(current, ['lodz'])

    def test_unknown_city_still_gets_the_list(self):
        """The 404 page needs the list precisely when there is no current city."""
        data = self.get(host='krakow.gdzienawesta.com')
        self.assertIsNone(data['current'])
        self.assertEqual({c['slug'] for c in data['cities']}, {'warszawa', 'lodz'})

    def test_inactive_cities_are_hidden(self):
        self.lodz.is_active = False
        self.lodz.save()
        self.assertEqual([c['slug'] for c in self.get()['cities']], ['warszawa'])

    def test_order_is_polish_alphabetical(self):
        City.objects.create(name='Gdańsk', calendar_id='g@example.com')
        self.assertEqual(
            [c['name'] for c in self.get()['cities']],
            ['Gdańsk', 'Łódź', 'Warszawa'],
        )
