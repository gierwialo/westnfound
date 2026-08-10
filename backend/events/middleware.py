"""Resolve which city a request is for, from the Host header.

    gdzienawesta.com          -> the default city
    www.gdzienawesta.com      -> the default city
    lodz.gdzienawesta.com     -> the city whose slug is "lodz"
    krakow.gdzienawesta.com   -> None, when no such city exists

A host that does not end in a configured base domain - a direct hit on the
server's IP address, a health check, an unrecognised proxy - resolves to the
default city. That is what this site did before cities existed, and keeping it
means the apex has no separate code path that only production exercises.
"""

from django.conf import settings

from .models import City


def _hostname(raw_host: str) -> str:
    """Bare lowercase hostname: no port, no trailing dot, no brackets."""
    host = (raw_host or '').strip().lower().rstrip('.')
    if host.startswith('['):            # IPv6 literal, e.g. [::1]:8000
        return host.partition(']')[0].lstrip('[')
    return host.partition(':')[0]


def resolve_city(raw_host: str, base_domains):
    """Return (city, is_unknown_subdomain).

    ``is_unknown_subdomain`` separates "this host names a city we do not have"
    from "there are no cities at all", so callers can tell a 404 for Kraków
    apart from an empty database.
    """
    host = _hostname(raw_host)

    for base in base_domains:
        if host == base or host == f'www.{base}':
            return City.default(), False

        suffix = f'.{base}'
        if host.endswith(suffix):
            label = host[:-len(suffix)]
            if label == 'www':
                return City.default(), False
            # Deeper names (a.b.gdzienawesta.com) are not city addresses.
            if not label or '.' in label:
                return None, True
            city = City.objects.filter(slug=label, is_active=True).first()
            return (city, False) if city else (None, True)

    # Unrecognised host: behave exactly as before cities existed.
    return City.default(), False


class CityMiddleware:
    """Attaches ``request.city`` and ``request.city_is_unknown``."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request.city, request.city_is_unknown = resolve_city(
            request.get_host(), settings.CITY_BASE_DOMAINS
        )
        return self.get_response(request)
