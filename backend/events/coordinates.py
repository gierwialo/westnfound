"""Where a city sits on the map, as the owner pastes it from Google Maps.

Right-clicking a place in Google Maps and clicking the numbers at the top of
the menu copies them as "50.0412, 21.9991": latitude first, a comma and a
space, and as many decimals as Google feels like. One field that takes exactly
that is one paste; two number fields would be two paste-and-trim jobs.
"""
import re

from django.core.exceptions import ValidationError

# Poland is 49.00-54.84 N and 14.12-24.15 E. The margin keeps a city on the
# border (Słubice, Cieszyn, Przemyśl) on the right side of the check without
# letting through the mistake the check exists for, which lands far away.
LATITUDE_RANGE = (48.5, 55.3)
LONGITUDE_RANGE = (13.6, 24.7)

# Six decimals is about ten centimetres: more than the map can draw, and
# enough that pasting a value back in does not change it.
PRECISION = 6

_PAIR = re.compile(r'^\s*(-?\d+(?:\.\d+)?)\s*[,;\s]\s*(-?\d+(?:\.\d+)?)\s*$')


def _in_poland(latitude, longitude):
    return (
        LATITUDE_RANGE[0] <= latitude <= LATITUDE_RANGE[1]
        and LONGITUDE_RANGE[0] <= longitude <= LONGITUDE_RANGE[1]
    )


def parse_coordinates(text):
    """Return (latitude, longitude), or (None, None) for an empty field.

    Empty is allowed: the city is still listed, just without a dot on the map.
    """
    if not text or not text.strip():
        return None, None

    match = _PAIR.match(text)
    if match is None:
        raise ValidationError(
            f'"{text.strip()}" is not a pair of coordinates. '
            'Paste them as Google Maps copies them, e.g. "50.0412, 21.9991".'
        )

    latitude, longitude = (round(float(value), PRECISION) for value in match.groups())
    if _in_poland(latitude, longitude):
        return latitude, longitude

    shown = f'{match.group(1)}, {match.group(2)}'
    # Typing the numbers in the wrong order is the likely mistake, and the
    # only one worth a hint: anything else is simply a different place.
    if _in_poland(longitude, latitude):
        raise ValidationError(
            f'{shown} is outside Poland. Are latitude and longitude swapped?'
        )
    raise ValidationError(f'{shown} is outside Poland.')


def format_coordinates(latitude, longitude):
    """The field's value for a saved city, in the format it was pasted in."""
    if latitude is None or longitude is None:
        return ''
    # Not :g, which keeps six significant digits and would quietly cut
    # 21.99912 to 21.9991 every time the city is saved.
    return f'{latitude}, {longitude}'
