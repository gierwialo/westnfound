"""Turn the Calendar model into City.

The production database holds exactly one row - the Warsaw calendar, named
after the community that runs it ("Warsaw Westies Dance"). Since name now
means the city name, that row is renamed and given the slug and default flag
here rather than by hand after deployment.
"""

from django.db import migrations, models


def fill_city_fields(apps, schema_editor):
    City = apps.get_model('events', 'City')

    warsaw = City.objects.filter(calendar_id='warsawwestiesdance@gmail.com').first()
    if warsaw is not None:
        warsaw.name = 'Warszawa'
        warsaw.slug = 'warszawa'
        warsaw.is_default = True
        warsaw.save()

    # Any other row (a development database, say) gets a slug derived from its
    # name so the unique constraint below can be applied.
    from events.slugs import to_slug
    for city in City.objects.exclude(slug='warszawa'):
        if not city.slug:
            city.slug = to_slug(city.name) or f'city-{city.pk}'
            city.save()

    # The apex needs a default even if the Warsaw row is missing.
    if not City.objects.filter(is_default=True).exists():
        first = City.objects.order_by('pk').first()
        if first is not None:
            first.is_default = True
            first.save()


def unfill(apps, schema_editor):
    """Nothing to undo: the fields themselves are removed by the reverse of
    AddField, and the old name is not worth restoring."""


class Migration(migrations.Migration):

    dependencies = [
        ('events', '0002_alter_calendar_options_alter_calendar_calendar_id_and_more'),
    ]

    operations = [
        migrations.RenameModel(old_name='Calendar', new_name='City'),
        migrations.AlterModelOptions(
            name='city',
            options={
                'ordering': ['slug'],
                'verbose_name': 'City',
                'verbose_name_plural': 'Cities',
            },
        ),
        migrations.AlterField(
            model_name='city',
            name='name',
            field=models.CharField(
                help_text="City name with diacritics, as displayed (e.g. 'Łódź')",
                max_length=200,
            ),
        ),
        # Added without the unique constraint so existing rows can be filled in.
        migrations.AddField(
            model_name='city',
            name='slug',
            field=models.SlugField(default='', max_length=63),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='city',
            name='is_active',
            field=models.BooleanField(
                default=True, help_text='Whether the city is active'
            ),
        ),
        migrations.AddField(
            model_name='city',
            name='is_default',
            field=models.BooleanField(
                default=False,
                help_text='City shown on gdzienawesta.com itself. Exactly one city has this.',
            ),
        ),
        migrations.RunPython(fill_city_fields, unfill),
        migrations.AlterField(
            model_name='city',
            name='slug',
            field=models.SlugField(
                help_text='Subdomain label, ASCII only (e.g. \'lodz\' for lodz.gdzienawesta.com). '
                          'Filled in from the name when left blank. Changing it breaks '
                          'every link already shared for this city.',
                max_length=63,
                unique=True,
            ),
        ),
    ]
