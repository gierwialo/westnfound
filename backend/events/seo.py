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
from django.http import HttpResponse, HttpResponseNotFound, HttpResponseRedirect
from django.views import View
from xml.sax.saxutils import escape

from .middleware import _hostname, canonical_host, hub_host, scheme_for
from .models import City

# Addresses worth offering to a crawler, in the site's own language. The page
# answers to /calendar as well, but the two spellings are one page, so listing
# both would be asking Google to pick a favourite between duplicates.
CITY_PATHS = ['/', '/kalendarz']


class RobotsView(View):
    """robots.txt naming this host's sitemap.

    Cloudflare already appends a managed block with its own rules for AI
    crawlers; that block is added to whatever the origin returns, so what
    matters here is that the origin returns robots.txt rather than a page.
    """

    def get(self, request):
        host = request.get_host()
        # Point at the sitemap of the address this host's pages actually keep:
        # the apex for the map, whether asked on the apex or on www, and the
        # city's own subdomain for everything else.
        named = (
            hub_host(host, settings.CITY_BASE_DOMAINS)
            or canonical_host(host, getattr(request, 'city', None),
                              settings.CITY_BASE_DOMAINS)
            or host
        )
        lines = [
            'User-agent: *',
            'Allow: /',
            '',
            # The admin panel lives behind a configurable path and is not
            # linked from anywhere; naming it here would only advertise it.
            f'Sitemap: {scheme_for(named)}://{named}/sitemap.xml',
            '',
        ]
        response = HttpResponse('\n'.join(lines), content_type='text/plain; charset=utf-8')
        # What this file should live for. Whether anyone downstream agrees is
        # another matter: measured 2026-08-16, the zone's Browser Cache TTL of
        # four hours behaves as a floor rather than a default, so Cloudflare
        # rewrites max-age=300 to max-age=14400 on the way out, while
        # styles.css keeps the year it asks for because a year is above the
        # floor. Neither no-cache nor a small number survives that on its own.
        #
        # It takes a cache rule in Cloudflare, scoped to this path, for the
        # value below to be the one a reader actually sees. The header stays
        # regardless: it is the origin saying what it means, and it is what
        # the rule will defer to.
        response['Cache-Control'] = 'public, max-age=300'
        return response


class SitemapView(View):
    """The addresses of this host; on the apex, the map and every city.

    A sitemap normally covers one host. The apex lists the cities on purpose:
    it is the one address people and crawlers arrive at knowing nothing else.
    Google accepts this from a domain property, which covers every subdomain
    at once. Each city's own sitemap then lists that city's pages.
    """

    def get(self, request):
        host = request.get_host()
        scheme = scheme_for(host)
        city = getattr(request, 'city', None)

        apex = hub_host(host, settings.CITY_BASE_DOMAINS)
        if apex is not None:
            # www shows the apex's page, so it defers to the apex's sitemap.
            if _hostname(host) != apex:
                return HttpResponseRedirect(f'{scheme}://{apex}/sitemap.xml')
            urls = [f'{scheme}://{apex}/'] + [
                f'{scheme}://{other.slug}.{apex}/'
                for other in City.objects.filter(is_active=True)
            ]
            return _urlset(urls)

        # A host naming no city we serve shows an apology, not a page worth
        # indexing - offering a sitemap for it would invite exactly that.
        if city is None:
            return HttpResponseNotFound(
                'No city is served at this address\n',
                content_type='text/plain; charset=utf-8',
            )

        return _urlset([f'{scheme}://{host}{path}' for path in CITY_PATHS])


def _urlset(urls):
    body = ['<?xml version="1.0" encoding="UTF-8"?>',
            '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for url in urls:
        body.append(f'  <url><loc>{escape(url)}</loc></url>')
    body.append('</urlset>')
    body.append('')
    return HttpResponse('\n'.join(body), content_type='application/xml; charset=utf-8')
