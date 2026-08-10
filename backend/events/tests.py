from django.core.exceptions import ValidationError
from django.test import TestCase

from .models import City
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
