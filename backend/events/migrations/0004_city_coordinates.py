"""Give cities a place on the map.

Two nullable columns and nothing else touched, so a running server that does
not know them yet keeps reading and writing the table as before.

The cities gdzienawesta.com served when the map arrived get their centres
filled in here, so the map is not empty on the day it goes live. Only where
the slug matches and the city has no coordinates yet: a development database
with other cities is left alone, and the admin panel stays the place to
correct them.
"""

from django.db import migrations, models

CITY_CENTRES = {
    'bydgoszcz': (53.1235, 18.0084),
    'gliwice': (50.2945, 18.6714),
    'katowice': (50.2649, 19.0238),
    'krakow': (50.0614, 19.9366),
    'lodz': (51.7592, 19.456),
    'poznan': (52.4064, 16.9252),
    'rzeszow': (50.0412, 21.9991),
    'szczecin': (53.4285, 14.5528),
    'warszawa': (52.2297, 21.0122),
    'wroclaw': (51.1079, 17.0385),
}


def fill_city_centres(apps, schema_editor):
    City = apps.get_model('events', 'City')
    for slug, (latitude, longitude) in CITY_CENTRES.items():
        City.objects.filter(slug=slug, latitude__isnull=True).update(
            latitude=latitude, longitude=longitude
        )


class Migration(migrations.Migration):

    dependencies = [
        ('events', '0003_calendar_to_city'),
    ]

    operations = [
        migrations.AddField(
            model_name='city',
            name='latitude',
            field=models.FloatField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='city',
            name='longitude',
            field=models.FloatField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name='city',
            name='is_default',
            field=models.BooleanField(default=False, help_text='The city behind the addresses gdzienawesta.com had before the map: /kalendarz.ics, /kalendarz and the API. Exactly one city has this.'),
        ),
        # Nothing to undo: reversing AddField drops the columns.
        migrations.RunPython(fill_city_centres, migrations.RunPython.noop),
    ]
