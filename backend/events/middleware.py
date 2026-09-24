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


def base_domain_for(raw_host: str, base_domains):
    """Which configured base domain this request arrived on, if any.

    Used to build links to sibling cities that stay on the domain the visitor
    is already using, so local work on lvh.me does not link out to production.
    """
    host = _hostname(raw_host)
    for base in base_domains:
        if host == base or host == f'www.{base}' or host.endswith(f'.{base}'):
            return base
    return None


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
def hub_host(raw_host: str, base_domains):
    """The apex this request is on when it asks for the map of cities, or None.

    The apex and www are where the map lives. They still resolve to the default
    city, because the API and the subscription feed there keep answering as
    Warsaw - subscribers and old versions of the app rely on those addresses.
    Only the pages a person reads have moved.
    """
    host = _hostname(raw_host)
    base = base_domain_for(raw_host, base_domains)
    if base is not None and host in (base, f'www.{base}'):
        return base
    return None


def canonical_host(raw_host: str, city, base_domains):
    """The one address this city's pages live at, or None if we are there.

    Every city lives on its own subdomain, the default city included. The
    default city also answers on the apex and www, which used to be its home;
    now that the apex is the map, those addresses hand its pages on to the
    subdomain.
    """
    base = base_domain_for(raw_host, base_domains)
    if base is None or city is None:
        # An unrecognised host or a subdomain naming no city we serve: nothing
        # to redirect to that would be more correct than where we already are.
        return None
    home = f'{city.slug}.{base}'
    return None if _hostname(raw_host) == home else home


# Hosts where https is not what the visitor uses. Everything else is public
# and sits behind Cloudflare, which terminates TLS - and the origin has no way
# to tell, because the edge layer overwrites X-Forwarded-Proto with its own
# scheme.
LOCAL_HOSTS = ('localhost', '127.0.0.1', '::1', 'lvh.me')


def scheme_for(raw_host: str) -> str:
    host = _hostname(raw_host)
    if host in LOCAL_HOSTS or host.endswith('.lvh.me') or host.endswith('.local'):
        return 'http'
    return 'https'
