from unittest.mock import Mock, patch

import re
from datetime import datetime, timedelta, timezone as dt_timezone
from pathlib import Path

import requests
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.test import TestCase, override_settings
from django.utils import timezone

from .coordinates import format_coordinates, parse_coordinates
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

    def test_feed_says_when_it_was_fetched_from_google(self):
        """The status page reads this to say "fetched 6 minutes ago"."""
        before = timezone.now().replace(microsecond=0)
        with patch('events.services.requests.get', return_value=_google_says()):
            response = self.client.get('/kalendarz.ics', HTTP_HOST='gdzienawesta.com')

        fetched = datetime.strptime(
            response['X-Feed-Fetched'], '%Y-%m-%dT%H:%M:%SZ'
        ).replace(tzinfo=dt_timezone.utc)
        self.assertGreaterEqual(fetched, before)
        self.assertLessEqual(fetched, timezone.now())

    def test_a_stale_copy_keeps_the_time_of_its_fetch(self):
        """Serving the last good copy must not pass it off as a new one."""
        with patch('events.services.requests.get', return_value=_google_says()):
            first = self.client.get('/kalendarz.ics', HTTP_HOST='gdzienawesta.com')

        cache.delete('ics:fresh:warsawwestiesdance@gmail.com')
        with patch('events.services.requests.get', side_effect=requests.Timeout()):
            stale = self.client.get('/kalendarz.ics', HTTP_HOST='gdzienawesta.com')

        self.assertEqual(stale['X-Feed-Stale'], '1')
        self.assertEqual(stale['X-Feed-Fetched'], first['X-Feed-Fetched'])

    def test_a_copy_cached_before_the_time_was_kept_still_serves(self):
        """Copies from before this header existed live on for up to a week."""
        cache.set('ics:fresh:warsawwestiesdance@gmail.com', ICS)
        with patch('events.services.requests.get') as get:
            response = self.client.get('/kalendarz.ics', HTTP_HOST='gdzienawesta.com')

        get.assert_not_called()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, ICS)
        self.assertNotIn('X-Feed-Fetched', response)


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

    def test_every_city_links_to_its_subdomain_the_default_one_too(self):
        """The apex is the map, so linking Warsaw there would lead back to it."""
        by_slug = {c['slug']: c for c in self.get()['cities']}
        self.assertEqual(by_slug['warszawa']['url'], '//warszawa.gdzienawesta.com')
        self.assertEqual(by_slug['lodz']['url'], '//lodz.gdzienawesta.com')

    def test_links_stay_on_the_domain_the_visitor_is_using(self):
        """Working on lvh.me must not produce links out to production."""
        by_slug = {c['slug']: c for c in self.get(host='lodz.lvh.me')['cities']}
        self.assertEqual(by_slug['lodz']['url'], '//lodz.lvh.me')
        self.assertEqual(by_slug['warszawa']['url'], '//warszawa.lvh.me')

    def test_coordinates_are_handed_over(self):
        self.lodz.latitude, self.lodz.longitude = 51.7592, 19.456
        self.lodz.save()
        by_slug = {c['slug']: c for c in self.get()['cities']}
        self.assertEqual(
            (by_slug['lodz']['latitude'], by_slug['lodz']['longitude']),
            (51.7592, 19.456),
        )

    def test_a_city_without_coordinates_is_still_listed(self):
        """It belongs on the list; only the dot on the map is missing."""
        by_slug = {c['slug']: c for c in self.get()['cities']}
        self.assertIsNone(by_slug['warszawa']['latitude'])
        self.assertIsNone(by_slug['warszawa']['longitude'])

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


class CitiesNextTests(TestCase):
    """The second line of every row in the map's list."""

    def setUp(self):
        City.objects.create(name='Warszawa', calendar_id='w@example.com', is_default=True)
        City.objects.create(name='Łódź', calendar_id='l@example.com')
        City.objects.create(name='Gdańsk', calendar_id='g@example.com', is_active=False)

    def get(self, next_events, host='gdzienawesta.com'):
        asked = []

        def fake(_service, calendar_id):
            asked.append(calendar_id)
            return next_events.get(calendar_id)

        with patch.object(GoogleCalendarService, 'get_next_event', fake):
            response = self.client.get('/api/cities/next/', HTTP_HOST=host)
        self.assertEqual(response.status_code, 200)
        return response.json(), asked

    def test_every_active_city_gets_its_own_next_event(self):
        data, asked = self.get({
            'w@example.com': {
                'title': 'Praktis', 'start': '2026-09-26T19:00:00+02:00',
                'end': '2026-09-26T22:00:00+02:00', 'description': 'long',
                'location': 'Somewhere', 'calendar_id': 'w@example.com',
            },
            'l@example.com': {
                'title': 'Impreza', 'start': '2026-10-10T21:00:00+02:00',
                'end': '2026-10-11T01:00:00+02:00', 'description': '',
                'location': '', 'calendar_id': 'l@example.com',
            },
        })
        self.assertEqual(sorted(asked), ['l@example.com', 'w@example.com'])
        self.assertEqual(data['cities'], [
            {'slug': 'lodz', 'event': {
                'title': 'Impreza', 'start': '2026-10-10T21:00:00+02:00',
                'end': '2026-10-11T01:00:00+02:00',
            }},
            {'slug': 'warszawa', 'event': {
                'title': 'Praktis', 'start': '2026-09-26T19:00:00+02:00',
                'end': '2026-09-26T22:00:00+02:00',
            }},
        ])

    def test_a_quiet_city_is_listed_with_no_event(self):
        """Not left out: the list shows the city and no second line."""
        data, _ = self.get({})
        self.assertEqual(
            data['cities'],
            [{'slug': 'lodz', 'event': None}, {'slug': 'warszawa', 'event': None}],
        )

    def test_the_answer_is_the_same_on_every_host(self):
        """Even one naming no city: the map is everyone's way in."""
        on_apex, _ = self.get({})
        on_unknown, _ = self.get({}, host='krakow.gdzienawesta.com')
        self.assertEqual(on_apex, on_unknown)

    def test_no_cities_at_all_is_an_empty_list_not_an_error(self):
        City.objects.all().delete()
        data, _ = self.get({})
        self.assertEqual((data['count'], data['cities']), (0, []))


class CoordinatesTests(TestCase):
    """The one field the owner pastes a Google Maps location into."""

    def test_the_format_google_maps_copies(self):
        self.assertEqual(parse_coordinates('50.0412, 21.9991'), (50.0412, 21.9991))

    def test_google_sometimes_copies_many_more_decimals(self):
        self.assertEqual(
            parse_coordinates('50.04123456789, 21.99912345678'),
            (50.041235, 21.999123),
        )

    def test_spacing_is_forgiven(self):
        self.assertEqual(parse_coordinates(' 50.0412,21.9991 '), (50.0412, 21.9991))
        self.assertEqual(parse_coordinates('50.0412 21.9991'), (50.0412, 21.9991))

    def test_empty_means_no_dot_on_the_map(self):
        self.assertEqual(parse_coordinates(''), (None, None))
        self.assertEqual(parse_coordinates('   '), (None, None))

    def test_swapped_order_is_caught_with_a_hint(self):
        with self.assertRaisesMessage(ValidationError, 'Are latitude and longitude swapped?'):
            parse_coordinates('21.9991, 50.0412')

    def test_somewhere_else_is_caught_without_the_hint(self):
        with self.assertRaises(ValidationError) as caught:
            parse_coordinates('40.4168, -3.7038')
        self.assertIn('outside Poland', str(caught.exception))
        self.assertNotIn('swapped', str(caught.exception))

    def test_a_city_on_the_border_is_accepted(self):
        for pair in ('52.3480, 14.5530', '49.7497, 18.6320', '49.7838, 22.7677'):
            with self.subTest(pair=pair):
                parse_coordinates(pair)

    def test_something_that_is_not_a_pair(self):
        for text in ('50.0412', 'Rzeszów', '50,0412, 21,9991'):
            with self.subTest(text=text):
                with self.assertRaisesMessage(ValidationError, 'not a pair'):
                    parse_coordinates(text)

    def test_a_saved_pair_reads_back_as_it_was_pasted(self):
        latitude, longitude = parse_coordinates('50.041235, 21.999123')
        self.assertEqual(format_coordinates(latitude, longitude), '50.041235, 21.999123')
        self.assertEqual(format_coordinates(None, None), '')

    def test_half_a_pair_is_refused_by_the_model(self):
        city = City(name='Rzeszów', calendar_id='r@example.com', latitude=50.0412)
        with self.assertRaises(ValidationError):
            city.full_clean()


class CityAdminFormTests(TestCase):
    def form(self, coordinates, instance=None):
        from .admin import CityForm

        return CityForm(data={
            'name': 'Rzeszów', 'slug': 'rzeszow', 'calendar_id': 'r@example.com',
            'coordinates': coordinates, 'is_active': 'on',
        }, instance=instance)

    def test_pasted_coordinates_are_saved_into_both_columns(self):
        form = self.form('50.0412, 21.9991')
        self.assertTrue(form.is_valid(), form.errors)
        city = form.save()
        self.assertEqual((city.latitude, city.longitude), (50.0412, 21.9991))

    def test_the_error_is_shown_on_the_field(self):
        form = self.form('21.9991, 50.0412')
        self.assertFalse(form.is_valid())
        self.assertIn('swapped', form.errors['coordinates'][0])

    def test_clearing_the_field_takes_the_city_off_the_map(self):
        city = City.objects.create(
            name='Rzeszów', slug='rzeszow', calendar_id='r@example.com',
            latitude=50.0412, longitude=21.9991,
        )
        form = self.form('', instance=city)
        self.assertTrue(form.is_valid(), form.errors)
        city = form.save()
        self.assertEqual((city.latitude, city.longitude), (None, None))

    def test_an_existing_city_shows_its_coordinates(self):
        from .admin import CityForm

        city = City.objects.create(
            name='Rzeszów', calendar_id='r@example.com', latitude=50.0412, longitude=21.9991,
        )
        self.assertEqual(CityForm(instance=city).initial['coordinates'], '50.0412, 21.9991')


@override_settings(CITY_BASE_DOMAINS=['gdzienawesta.com'])
class RobotsTests(TestCase):
    def setUp(self):
        City.objects.create(name='Warszawa', slug='warszawa',
                            calendar_id='w@example.com', is_default=True)

    def test_apex_names_its_own_sitemap(self):
        response = self.client.get('/robots.txt', HTTP_HOST='gdzienawesta.com')
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response['Content-Type'].startswith('text/plain'))
        self.assertIn('Sitemap: https://gdzienawesta.com/sitemap.xml',
                      response.content.decode())

    def test_each_city_names_the_sitemap_of_its_own_host(self):
        response = self.client.get('/robots.txt', HTTP_HOST='lodz.gdzienawesta.com')
        self.assertIn('Sitemap: https://lodz.gdzienawesta.com/sitemap.xml',
                      response.content.decode())

    def test_it_is_not_a_web_page(self):
        # The whole point: this path used to fall through to index.html.
        body = self.client.get('/robots.txt', HTTP_HOST='gdzienawesta.com').content
        self.assertNotIn(b'<html', body)

    def test_it_names_its_own_lifetime_rather_than_leaving_it_to_cloudflare(self):
        # An explicit max-age is respected; no-cache is not, and the four-hour
        # default takes its place.
        response = self.client.get('/robots.txt', HTTP_HOST='gdzienawesta.com')
        self.assertEqual(response['Cache-Control'], 'public, max-age=300')

    def test_local_development_is_not_told_to_use_https(self):
        response = self.client.get('/robots.txt', HTTP_HOST='localhost:8000')
        self.assertIn('Sitemap: http://localhost:8000/sitemap.xml',
                      response.content.decode())


@override_settings(CITY_BASE_DOMAINS=['gdzienawesta.com'])
class SitemapTests(TestCase):
    def setUp(self):
        City.objects.create(name='Warszawa', slug='warszawa',
                            calendar_id='w@example.com', is_default=True)
        City.objects.create(name='Łódź', slug='lodz', calendar_id='l@example.com')
        City.objects.create(name='Kraków', slug='krakow', calendar_id='k@example.com')

    def _urls(self, host):
        response = self.client.get('/sitemap.xml', HTTP_HOST=host)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response['Content-Type'].startswith('application/xml'))
        import re
        return re.findall(r'<loc>([^<]+)</loc>', response.content.decode())

    def test_apex_lists_the_map_and_every_city(self):
        self.assertEqual(self._urls('gdzienawesta.com'), [
            'https://gdzienawesta.com/',
            'https://krakow.gdzienawesta.com/',
            'https://lodz.gdzienawesta.com/',
            'https://warszawa.gdzienawesta.com/',
        ])

    def test_the_default_city_has_a_sitemap_of_its_own(self):
        """It used to be folded into the apex's; now it lives on its subdomain."""
        self.assertEqual(self._urls('warszawa.gdzienawesta.com'), [
            'https://warszawa.gdzienawesta.com/',
            'https://warszawa.gdzienawesta.com/kalendarz',
        ])

    def test_www_defers_to_the_apex(self):
        response = self.client.get('/sitemap.xml', HTTP_HOST='www.gdzienawesta.com')
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response['Location'], 'https://gdzienawesta.com/sitemap.xml')

    def test_a_city_lists_only_its_own_addresses(self):
        urls = self._urls('lodz.gdzienawesta.com')
        self.assertEqual(urls, ['https://lodz.gdzienawesta.com/',
                                'https://lodz.gdzienawesta.com/kalendarz'])

    def test_the_english_spelling_is_left_out_as_a_duplicate(self):
        self.assertNotIn('https://lodz.gdzienawesta.com/calendar',
                         self._urls('lodz.gdzienawesta.com'))

    def test_inactive_cities_are_not_offered_to_crawlers(self):
        City.objects.filter(slug='krakow').update(is_active=False)
        self.assertNotIn('https://krakow.gdzienawesta.com/',
                         self._urls('gdzienawesta.com'))

    def test_unknown_subdomain_has_no_sitemap(self):
        # That host shows an apology, not a page worth indexing.
        response = self.client.get('/sitemap.xml', HTTP_HOST='gdansk.gdzienawesta.com')
        self.assertEqual(response.status_code, 404)
        self.assertNotIn(b'<loc>', response.content)


@override_settings(CITY_BASE_DOMAINS=['gdzienawesta.com'])
class DocumentTests(TestCase):
    """The pages themselves, with the city filled in before anyone runs JS."""

    PAGE = ('<!DOCTYPE html>\n<html lang="pl">\n<head>\n'
            '<meta name="description" content="wyjściowy opis">\n'
            '<title>Wyjściowy tytuł</title>\n</head>\n'
            '<body><script src="app.js?v=abc"></script>\n'
            '<!-- gtag G-FJYJF645WS --></body>\n</html>\n')

    def setUp(self):
        import tempfile
        from events import documents

        self.dir = Path(tempfile.mkdtemp())
        (self.dir / 'index.html').write_text(self.PAGE, encoding='utf-8')
        (self.dir / 'calendar.html').write_text(self.PAGE, encoding='utf-8')
        (self.dir / 'cities.html').write_text(
            self.PAGE.replace('<body>', '<body><ul>\n<!-- cities:list -->\n</ul>'),
            encoding='utf-8')
        self._old_dir = documents.FRONTEND_DIR
        documents.FRONTEND_DIR = self.dir
        documents._cache.clear()
        self.addCleanup(self._restore)

        City.objects.create(name='Warszawa', slug='warszawa',
                            calendar_id='w@example.com', is_default=True)
        City.objects.create(name='Łódź', slug='lodz', calendar_id='l@example.com')

    def _restore(self):
        from events import documents
        documents.FRONTEND_DIR = self._old_dir
        documents._cache.clear()

    def _head(self, path, host):
        response = self.client.get(path, HTTP_HOST=host)
        self.assertEqual(response.status_code, 200)
        body = response.content.decode()
        import re
        return (re.search(r'<title>(.*?)</title>', body).group(1),
                re.search(r'name="description" content="([^"]*)"', body).group(1),
                body)

    def test_each_city_gets_its_own_title(self):
        warsaw, _, _ = self._head('/', 'warszawa.gdzienawesta.com')
        lodz, _, _ = self._head('/', 'lodz.gdzienawesta.com')
        self.assertEqual(warsaw, 'Gdzie na Westa? - Warszawa')
        self.assertEqual(lodz, 'Gdzie na Westa? - Łódź')

    def test_each_city_gets_its_own_description(self):
        _, warsaw, _ = self._head('/', 'warszawa.gdzienawesta.com')
        _, lodz, _ = self._head('/', 'lodz.gdzienawesta.com')
        self.assertIn('Warszawa', warsaw)
        self.assertIn('Łódź', lodz)
        self.assertNotEqual(warsaw, lodz)

    def test_the_cities_no_longer_serve_an_identical_document(self):
        # The whole point: three hosts used to answer byte for byte the same.
        _, _, warsaw = self._head('/', 'warszawa.gdzienawesta.com')
        _, _, lodz = self._head('/', 'lodz.gdzienawesta.com')
        self.assertNotEqual(warsaw, lodz)

    def test_no_description_promises_workshops(self):
        """The calendars are asked not to carry them (M8)."""
        for path, host in (('/', 'gdzienawesta.com'), ('/', 'lodz.gdzienawesta.com'),
                           ('/kalendarz', 'lodz.gdzienawesta.com')):
            _, description, _ = self._head(path, host)
            self.assertNotIn('warsztat', description, host + path)

    def test_a_single_city_is_not_named(self):
        City.objects.filter(slug='lodz').delete()
        title, description, _ = self._head('/', 'warszawa.gdzienawesta.com')
        self.assertEqual(title, 'Gdzie na Westa?')
        self.assertNotIn('w mieście', description)

    def test_the_calendar_page_names_its_city(self):
        title, description, _ = self._head('/kalendarz', 'lodz.gdzienawesta.com')
        self.assertEqual(title, 'Gdzie na Westa? - Kalendarz - Łódź')
        self.assertIn('Łódź', description)

    def test_every_spelling_of_the_calendar_page_answers(self):
        for path in ('/kalendarz', '/kalendarz/', '/calendar', '/calendar/'):
            self.assertEqual(self.client.get(path, HTTP_HOST='lodz.gdzienawesta.com')
                             .status_code, 200, path)

    def test_everything_else_in_the_page_is_handed_over_untouched(self):
        # Analytics and the ?v= stamps are written into these files after
        # deployment. Losing them here would be silent.
        for host in ('gdzienawesta.com', 'lodz.gdzienawesta.com'):
            _, _, body = self._head('/', host)
            self.assertIn('app.js?v=abc', body, host)
            self.assertIn('G-FJYJF645WS', body, host)
            self.assertIn('<html lang="pl">', body, host)

    def test_a_redeployed_page_is_picked_up(self):
        self._head('/', 'lodz.gdzienawesta.com')
        (self.dir / 'index.html').write_text(
            self.PAGE.replace('app.js?v=abc', 'app.js?v=zzz'), encoding='utf-8')
        import os
        os.utime(self.dir / 'index.html', ns=(0, 10 ** 18))
        _, _, body = self._head('/', 'lodz.gdzienawesta.com')
        self.assertIn('app.js?v=zzz', body)

    def test_an_unknown_city_still_gets_a_page(self):
        # The page itself explains it; answering with nothing would be worse.
        title, _, _ = self._head('/', 'gdansk.gdzienawesta.com')
        self.assertEqual(title, 'Gdzie na Westa?')


@override_settings(CITY_BASE_DOMAINS=['gdzienawesta.com', 'lvh.me'])
class HubTests(TestCase):
    """gdzienawesta.com itself: the map of cities, no longer Warsaw."""

    PAGE = ('<!DOCTYPE html>\n<html lang="pl">\n<head>\n'
            '<meta name="description" content="wyjściowy opis">\n'
            '<title>Wyjściowy tytuł</title>\n</head>\n'
            '<body><ul>\n<!-- cities:list -->\n</ul></body>\n</html>\n')

    def setUp(self):
        import tempfile
        from events import documents

        self.dir = Path(tempfile.mkdtemp())
        (self.dir / 'cities.html').write_text(self.PAGE, encoding='utf-8')
        (self.dir / 'index.html').write_text('<title>city page</title>', encoding='utf-8')
        self._old_dir = documents.FRONTEND_DIR
        documents.FRONTEND_DIR = self.dir
        documents._cache.clear()
        self.addCleanup(self._restore)

        City.objects.create(name='Warszawa', slug='warszawa',
                            calendar_id='w@example.com', is_default=True)
        City.objects.create(name='Łódź', slug='lodz', calendar_id='l@example.com')

    def _restore(self):
        from events import documents
        documents.FRONTEND_DIR = self._old_dir
        documents._cache.clear()

    def _page(self, host='gdzienawesta.com', path='/'):
        response = self.client.get(path, HTTP_HOST=host)
        self.assertEqual(response.status_code, 200)
        return response.content.decode()

    def _links(self, body):
        return re.findall(r'<a class="crow" href="([^"]+)"[^>]*><span class="tt"><b>([^<]+)</b>', body)

    def test_the_apex_is_the_map_not_warsaw(self):
        body = self._page()
        self.assertIn('<title>Gdzie na Westa?</title>', body)
        self.assertNotIn('city page', body)

    def test_every_city_is_linked_without_javascript(self):
        """Warsaw too: it is one of the cities now, on its own subdomain."""
        self.assertEqual(self._links(self._page()), [
            ('https://lodz.gdzienawesta.com/', 'Łódź'),
            ('https://warszawa.gdzienawesta.com/', 'Warszawa'),
        ])

    def test_inactive_cities_are_not_listed(self):
        City.objects.filter(slug='lodz').update(is_active=False)
        self.assertEqual([name for _, name in self._links(self._page())], ['Warszawa'])

    def test_each_row_carries_what_the_map_needs(self):
        """hub.js puts the dots on the map from these, without a request."""
        City.objects.filter(slug='lodz').update(latitude=51.7592, longitude=19.456)
        body = self._page()
        self.assertIn('data-slug="lodz" data-name="Łódź" data-lat="51.7592" data-lon="19.456"', body)
        # No coordinates: listed, with no dot to draw.
        self.assertIn('data-slug="warszawa" data-name="Warszawa">', body)

    def test_a_city_name_is_escaped(self):
        City.objects.create(name='A & <B>', slug='ab', calendar_id='ab@example.com')
        self.assertIn('<b>A &amp; &lt;B&gt;</b>', self._page())

    def test_the_description_counts_the_cities(self):
        """A new city in the admin panel reaches search results by itself."""
        body = self._page()
        self.assertIn('w 2 miastach w Polsce', body)
        City.objects.create(name='Kraków', slug='krakow', calendar_id='k@example.com')
        self.assertIn('w 3 miastach w Polsce', self._page())

    def test_one_city_is_not_counted(self):
        City.objects.filter(slug='lodz').delete()
        self.assertNotIn('miastach', self._page())

    def test_no_cities_at_all_is_still_a_page(self):
        City.objects.all().delete()
        self.assertEqual(self._links(self._page()), [])

    def test_the_file_name_spelling_is_the_map_too(self):
        self.assertEqual(self._links(self._page(path='/index.html')),
                         self._links(self._page()))

    def test_www_is_sent_to_the_apex(self):
        response = self.client.get('/', HTTP_HOST='www.gdzienawesta.com')
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response['Location'], 'https://gdzienawesta.com/')

    def test_it_points_at_itself_and_previews_as_the_map(self):
        body = self._page()
        self.assertIn('<link rel="canonical" href="https://gdzienawesta.com/">', body)
        self.assertIn('<meta property="og:url" content="https://gdzienawesta.com/">', body)
        self.assertIn('w 2 miastach', re.search(
            r'<meta property="og:description" content="([^"]*)"', body).group(1))
        self.assertNotIn('noindex', body)

    def test_local_work_links_to_local_cities(self):
        self.assertEqual(self._links(self._page(host='lvh.me'))[0],
                         ('http://lodz.lvh.me/', 'Łódź'))

    def test_the_api_on_the_apex_still_answers_as_the_default_city(self):
        """Old versions of the app and existing subscribers rely on it."""
        data = self.client.get('/api/calendar/', HTTP_HOST='gdzienawesta.com').json()
        self.assertEqual(data['city']['slug'], 'warszawa')


class TranslationParityTests(TestCase):
    """The Python strings must say what translations.js says.

    Without this, documents.py is a second copy of wording that lives in the
    frontend - and a copy nobody compares is a copy that drifts.
    """

    def _translations(self):
        from events import documents

        path = documents.FRONTEND_DIR / 'translations.js'
        if not path.exists():
            self.skipTest(f'translations.js not mounted at {path}')
        return path.read_text(encoding='utf-8').split('    en:', 1)[0]

    def test_wording_matches_the_frontend(self):
        from events import documents

        source = self._translations()
        for key, value in (
            ('title', documents.SITE_TITLE),
            ('calendarTitle', documents.CALENDAR_TITLE),
            ('metaDescription', documents.DESCRIPTION),
            ('metaDescriptionCity', documents.DESCRIPTION_CITY.format(city='{city}')),
            ('metaDescriptionCalendar', documents.DESCRIPTION_CALENDAR),
            ('metaDescriptionCalendarCity',
             documents.DESCRIPTION_CALENDAR_CITY.format(city='{city}')),
            ('metaDescriptionHub', documents.DESCRIPTION_HUB.format(count='{count}')),
        ):
            import re
            found = re.search(rf'^        {key}: "(.*?)",$', source, re.M)
            self.assertIsNotNone(found, f'{key} missing from translations.js')
            self.assertEqual(found.group(1), value, key)


@override_settings(CITY_BASE_DOMAINS=['gdzienawesta.com'])
class CanonicalHostTests(TestCase):
    """Every city lives on its own subdomain; the apex is the map."""

    def setUp(self):
        City.objects.create(name='Warszawa', slug='warszawa',
                            calendar_id='w@example.com', is_default=True)
        City.objects.create(name='Łódź', slug='lodz', calendar_id='l@example.com')

        import tempfile
        from events import documents
        self.dir = Path(tempfile.mkdtemp())
        page = ('<html lang="pl"><head>'
                '<meta name="description" content="x"><title>x</title>'
                '</head><body></body></html>')
        (self.dir / 'index.html').write_text(page, encoding='utf-8')
        (self.dir / 'calendar.html').write_text(page, encoding='utf-8')
        (self.dir / 'cities.html').write_text(page, encoding='utf-8')
        self._old = documents.FRONTEND_DIR
        documents.FRONTEND_DIR = self.dir
        documents._cache.clear()
        self.addCleanup(self._restore)

    def _restore(self):
        from events import documents
        documents.FRONTEND_DIR = self._old
        documents._cache.clear()

    def _canonical(self, path, host):
        body = self.client.get(path, HTTP_HOST=host).content.decode()
        import re
        found = re.search(r'<link rel="canonical" href="([^"]+)"', body)
        self.assertIsNotNone(found, f'brak canonical na {host}{path}')
        return found.group(1)

    def test_each_city_points_at_itself(self):
        self.assertEqual(self._canonical('/', 'warszawa.gdzienawesta.com'),
                         'https://warszawa.gdzienawesta.com/')
        self.assertEqual(self._canonical('/', 'lodz.gdzienawesta.com'),
                         'https://lodz.gdzienawesta.com/')

    def test_both_spellings_of_the_calendar_page_name_one_address(self):
        for path in ('/kalendarz', '/kalendarz/', '/calendar', '/calendar/'):
            self.assertEqual(self._canonical(path, 'lodz.gdzienawesta.com'),
                             'https://lodz.gdzienawesta.com/kalendarz', path)

    def test_the_apex_hands_the_default_citys_calendar_to_its_subdomain(self):
        """Bookmarks of gdzienawesta.com/kalendarz keep working."""
        for host in ('gdzienawesta.com', 'www.gdzienawesta.com'):
            for path in ('/kalendarz', '/kalendarz/', '/calendar', '/calendar/'):
                response = self.client.get(path, HTTP_HOST=host)
                self.assertEqual(response.status_code, 302, host + path)
                self.assertEqual(response['Location'],
                                 'https://warszawa.gdzienawesta.com/kalendarz', host + path)

    def test_www_is_the_apex_under_another_name(self):
        response = self.client.get('/', HTTP_HOST='www.gdzienawesta.com')
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response['Location'], 'https://gdzienawesta.com/')

    def test_the_redirect_is_temporary_because_the_apex_may_change_meaning(self):
        # 301 would sit in browser caches for months and outlive the decision.
        # The apex has just changed meaning once; that is the case in point.
        response = self.client.get('/kalendarz', HTTP_HOST='gdzienawesta.com')
        self.assertEqual(response.status_code, 302)

    def test_a_city_on_its_own_subdomain_is_not_redirected(self):
        for host in ('lodz.gdzienawesta.com', 'warszawa.gdzienawesta.com'):
            for path in ('/', '/kalendarz'):
                self.assertEqual(
                    self.client.get(path, HTTP_HOST=host).status_code, 200, host + path)

    def test_an_unknown_city_is_kept_out_of_the_index(self):
        body = self.client.get('/', HTTP_HOST='gdansk.gdzienawesta.com').content.decode()
        self.assertIn('<meta name="robots" content="noindex">', body)
        # No canonical: there is no other address this page is a copy of.
        self.assertNotIn('rel="canonical"', body)

    def test_a_real_city_is_not_marked_noindex(self):
        for host in ('gdzienawesta.com', 'warszawa.gdzienawesta.com',
                     'lodz.gdzienawesta.com'):
            body = self.client.get('/', HTTP_HOST=host).content.decode()
            self.assertNotIn('noindex', body, host)

    def test_the_calendar_page_of_an_unknown_city_too(self):
        body = self.client.get('/kalendarz',
                               HTTP_HOST='gdansk.gdzienawesta.com').content.decode()
        self.assertIn('<meta name="robots" content="noindex">', body)

    def test_an_unknown_city_is_not_redirected_anywhere(self):
        self.assertEqual(
            self.client.get('/', HTTP_HOST='gdansk.gdzienawesta.com').status_code, 200)

    def test_the_apex_does_not_redirect_to_itself(self):
        self.assertEqual(
            self.client.get('/', HTTP_HOST='gdzienawesta.com').status_code, 200)

    def test_robots_on_www_names_the_apex(self):
        body = self.client.get('/robots.txt',
                               HTTP_HOST='www.gdzienawesta.com').content.decode()
        self.assertIn('Sitemap: https://gdzienawesta.com/sitemap.xml', body)

    def test_robots_on_the_default_citys_subdomain_names_its_own(self):
        body = self.client.get('/robots.txt',
                               HTTP_HOST='warszawa.gdzienawesta.com').content.decode()
        self.assertIn('Sitemap: https://warszawa.gdzienawesta.com/sitemap.xml', body)


@override_settings(CITY_BASE_DOMAINS=['gdzienawesta.com'])
class LinkPreviewTests(TestCase):
    """What a chat window shows when someone pastes one of our addresses.

    Until these tags existed the site had none at all, so a link shared to
    Messenger - where roughly one visitor in five already comes from - was a
    bare blue line. The point of building them here rather than injecting them
    at the edge is the city: the edge does not know the cities, and teaching it
    would undo the rule that a new city is an entry in the admin panel.
    """

    def setUp(self):
        City.objects.create(name='Warszawa', slug='warszawa',
                            calendar_id='w@example.com', is_default=True)
        City.objects.create(name='Łódź', slug='lodz', calendar_id='l@example.com')

        import tempfile
        from events import documents
        self.dir = Path(tempfile.mkdtemp())
        page = ('<html lang="pl"><head>'
                '<meta name="description" content="x"><title>x</title>'
                '</head><body></body></html>')
        (self.dir / 'index.html').write_text(page, encoding='utf-8')
        (self.dir / 'calendar.html').write_text(page, encoding='utf-8')
        (self.dir / 'cities.html').write_text(page, encoding='utf-8')
        self._old = documents.FRONTEND_DIR
        documents.FRONTEND_DIR = self.dir
        documents._cache.clear()
        self.addCleanup(self._restore)

    def _restore(self):
        from events import documents
        documents.FRONTEND_DIR = self._old
        documents._cache.clear()

    def _meta(self, body, prop, attr='property'):
        found = re.search(rf'<meta {attr}="{prop}" content="([^"]*)"', body)
        self.assertIsNotNone(found, f'no {prop}')
        return found.group(1)

    def _body(self, host, path='/'):
        return self.client.get(path, HTTP_HOST=host).content.decode()

    def test_a_city_link_previews_with_that_citys_name(self):
        body = self._body('lodz.gdzienawesta.com')
        self.assertIn('Łódź', self._meta(body, 'og:title'))
        self.assertIn('Łódź', self._meta(body, 'og:description'))

    def test_the_preview_title_matches_the_page_title(self):
        # Two sources for one sentence is how they drift apart.
        for host in ('gdzienawesta.com', 'lodz.gdzienawesta.com'):
            body = self._body(host)
            title = re.search(r'<title>(.*?)</title>', body).group(1)
            description = self._meta(body, 'description', attr='name')
            self.assertEqual(self._meta(body, 'og:title'), title, host)
            self.assertEqual(self._meta(body, 'og:description'), description, host)

    def test_the_preview_address_is_the_canonical_one(self):
        body = self._body('lodz.gdzienawesta.com', '/calendar/')
        self.assertEqual(self._meta(body, 'og:url'),
                         'https://lodz.gdzienawesta.com/kalendarz')

    def test_the_image_is_absolute_because_it_lives_on_the_other_host(self):
        body = self._body('gdzienawesta.com')
        image = self._meta(body, 'og:image')
        self.assertEqual(image, 'https://app.gdzienawesta.com/og-image.png')
        self.assertEqual(self._meta(body, 'twitter:image', attr='name'), image)
        self.assertEqual(self._meta(body, 'og:image:width'), '1200')
        self.assertEqual(self._meta(body, 'og:image:height'), '630')
        self.assertEqual(self._meta(body, 'twitter:card', attr='name'),
                         'summary_large_image')

    def test_a_host_naming_no_city_gets_no_preview_at_all(self):
        # It is an apology with a list of cities. There is nothing to preview
        # and no honest address to point at - the same reason it is noindex.
        body = self._body('gdansk.gdzienawesta.com')
        self.assertNotIn('og:', body)
        self.assertNotIn('twitter:', body)

    def test_the_calendar_page_previews_as_the_calendar(self):
        body = self._body('lodz.gdzienawesta.com', '/kalendarz')
        self.assertIn('Kalendarz', self._meta(body, 'og:title'))


@override_settings(CITY_BASE_DOMAINS=['gdzienawesta.com'])
class FeedUrlTests(TestCase):
    """What a new subscriber is handed."""

    def setUp(self):
        City.objects.create(name='Warszawa', slug='warszawa',
                            calendar_id='w@example.com', is_default=True)
        City.objects.create(name='Łódź', slug='lodz', calendar_id='l@example.com')

    def _feed(self, host):
        import json
        response = self.client.get('/api/calendar/', HTTP_HOST=host)
        self.assertEqual(response.status_code, 200)
        return json.loads(response.content)['feed_url']

    def test_the_apex_hands_out_the_address_of_the_city_not_its_own(self):
        # The whole point: subscribing from the front page used to bind you to
        # gdzienawesta.com rather than to Warsaw.
        self.assertEqual(self._feed('gdzienawesta.com'),
                         'https://warszawa.gdzienawesta.com/kalendarz.ics')

    def test_a_city_hands_out_its_own(self):
        self.assertEqual(self._feed('lodz.gdzienawesta.com'),
                         'https://lodz.gdzienawesta.com/kalendarz.ics')

    def test_local_work_stays_on_the_domain_in_front_of_it(self):
        with override_settings(CITY_BASE_DOMAINS=['lvh.me']):
            self.assertEqual(self._feed('lvh.me'),
                             'http://warszawa.lvh.me/kalendarz.ics')


class SlotMarkerTests(TestCase):
    """Every page offers the same three places for a deployment's additions.

    A deployment may add things this repository does not carry - analytics,
    an announcement - and it finds the place for them by these comments. They
    are the whole contract: a page that loses one keeps working and simply
    stops getting the addition, with no error anywhere. Hence a test.
    """

    FRONTEND = Path(__file__).resolve().parents[2] / 'frontend'
    MARKERS = ('<!-- slot:head-end -->', '<!-- slot:body-start -->',
               '<!-- slot:body-end -->')

    def _pages(self):
        pages = sorted(self.FRONTEND.glob('*.html'))
        self.assertTrue(pages)
        return [(page.name, page.read_text(encoding='utf-8')) for page in pages]

    def test_every_page_has_each_marker_once(self):
        for name, html in self._pages():
            for marker in self.MARKERS:
                self.assertEqual(html.count(marker), 1, f'{name}: {marker}')

    def test_markers_sit_where_their_names_say(self):
        import re
        for name, html in self._pages():
            head_end = html.index('</head>')
            body_open = re.search(r'<body[^>]*>', html)
            body_close = html.index('</body>')
            self.assertLess(html.index(self.MARKERS[0]), head_end, name)
            # Nothing but whitespace between <body ...> and the first marker,
            # and between the last marker and </body>.
            self.assertEqual(
                html[body_open.end():html.index(self.MARKERS[1])].strip(), '', name)
            end = html.index(self.MARKERS[2]) + len(self.MARKERS[2])
            self.assertEqual(html[end:body_close].strip(), '', name)

    def test_no_page_has_a_bare_body_tag(self):
        # An older deployment matched a bare <body> to add its banner. Keeping
        # it out means a page never gets that and the marker's addition twice.
        for name, html in self._pages():
            self.assertNotIn('<body>', html, name)
