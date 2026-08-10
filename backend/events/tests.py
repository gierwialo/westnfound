from unittest.mock import patch

from django.core.exceptions import ValidationError
from django.test import TestCase

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
