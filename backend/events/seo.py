"""What search engines need: a robots.txt and a sitemap, both per city.

Neither existed before. `/sitemap.xml` and `/robots.txt` fell through to the
frontend's catch-all, which answers every unknown path with index.html - so
both returned a whole HTML document with status 200, and Google was left to
discover the site's addresses on its own. Since the city subdomains went live
the addresses are no longer discoverable by guessing: `lodz.gdzienawesta.com`
is nowhere in the served HTML, because the footer that links the cities is
built by JavaScript from /api/cities/.

Both responses depend on the Host header, exactly like the rest of the site.
"""

from django.conf import settings
from django.http import HttpResponse, HttpResponseNotFound
from django.views import View
from xml.sax.saxutils import escape

from .middleware import base_domain_for
from .models import City

# Addresses worth offering to a crawler, in the site's own language. The page
# answers to /calendar as well, but the two spellings are one page, so listing
# both would be asking Google to pick a favourite between duplicates.
CITY_PATHS = ['/', '/kalendarz']

# Hosts where https is not what the visitor is using. Everything else is
# public and behind Cloudflare, which terminates TLS - and the origin cannot
# tell, because the edge overwrites X-Forwarded-Proto with its own scheme.
LOCAL_HOSTS = ('localhost', '127.0.0.1', '::1', 'lvh.me')


def _scheme_for(host: str) -> str:
    bare = host.partition(':')[0]
    if bare in LOCAL_HOSTS or bare.endswith('.lvh.me') or bare.endswith('.local'):
        return 'http'
    return 'https'


def _host_of(city: City, base: str) -> str:
    """The address a city answers on: the apex for the default, else its own."""
    return base if city.is_default else f'{city.slug}.{base}'


class RobotsView(View):
    """robots.txt naming this host's sitemap.

    Cloudflare already appends a managed block with its own rules for AI
    crawlers; that block is added to whatever the origin returns, so what
    matters here is that the origin returns robots.txt rather than a page.
    """

    def get(self, request):
        host = request.get_host()
        lines = [
            'User-agent: *',
            'Allow: /',
            '',
            # The admin panel lives behind a configurable path and is not
            # linked from anywhere; naming it here would only advertise it.
            f'Sitemap: {_scheme_for(host)}://{host}/sitemap.xml',
            '',
        ]
        return HttpResponse('\n'.join(lines), content_type='text/plain; charset=utf-8')


class SitemapView(View):
    """The addresses of this host, plus every city when this is the apex.

    A sitemap normally covers one host. The apex lists the other cities on
    purpose: their subdomains appear in no served HTML, so a crawler that
    never runs our JavaScript has no other way to learn they exist. Google
    accepts this from a domain property, which covers every subdomain at once.
    """

    def get(self, request):
        host = request.get_host()
        scheme = _scheme_for(host)
        base = (
            base_domain_for(host, settings.CITY_BASE_DOMAINS)
            or settings.CITY_BASE_DOMAINS[0]
        )
        city = getattr(request, 'city', None)

        # A host naming no city we serve shows an apology, not a page worth
        # indexing - offering a sitemap for it would invite exactly that.
        if city is None:
            return HttpResponseNotFound(
                'No city is served at this address\n',
                content_type='text/plain; charset=utf-8',
            )

        urls = [f'{scheme}://{host}{path}' for path in CITY_PATHS]

        if city is not None and city.is_default:
            for other in City.objects.filter(is_active=True):
                if other.pk == city.pk:
                    continue
                urls.append(f'{scheme}://{_host_of(other, base)}/')

        body = ['<?xml version="1.0" encoding="UTF-8"?>',
                '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
        for url in urls:
            body.append(f'  <url><loc>{escape(url)}</loc></url>')
        body.append('</urlset>')
        body.append('')

        return HttpResponse('\n'.join(body), content_type='application/xml; charset=utf-8')
