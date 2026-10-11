"""The pages themselves, with their title and description filled in per city.

Until now nginx served frontend/index.html straight from disk, so every city
got a document identical to the byte - no city name, no events, an empty <h1>.
Alpine fills all of that in afterwards, which is fine for a person and not for
a crawler that has just been pointed at three subdomains by our own sitemap.

What this does NOT do is render the page. The static file stays the one place
the markup lives; this rewrites two tags in it and hands the rest over
untouched, so Google Analytics injected by post-deploy.sh and the ?v= stamps
added by stamp-assets.py both survive - they are in the same file, put there
after deployment and read here at request time.
"""

import os
import re
from pathlib import Path

from django.http import HttpResponse, HttpResponseRedirect
from django.views import View

from django.conf import settings

from .middleware import _hostname, canonical_host, hub_host, scheme_for
from .models import City

# A TEMPORARY redirect, not a permanent one, and that is a decision, not an
# oversight: a permanent redirect sits in browsers' memory for months and
# cannot be taken back. Switching to 301 means changing this one number.
REDIRECT_STATUS = 302

FRONTEND_DIR = Path(os.environ.get('FRONTEND_DIR', '/frontend'))

# Polish, because the server cannot know better: the visitor's choice lives in
# localStorage and arrives with no request. Alpine rewrites both tags for an
# English reader as soon as it runs - see updateTitle() in app.js, whose
# wording these strings deliberately match. TranslationParityTests keeps them
# matching; without it this file would be a second, quietly diverging copy.
SITE_TITLE = 'Gdzie na Westa?'
CALENDAR_TITLE = 'Kalendarz'
#
# Practices, not workshops: the calendars are asked not to carry workshops,
# so promising them in a search result promised what the page does not show.
DESCRIPTION = (
    'Najbliższe imprezy i praktisy West Coast Swing '
    '— data, miejsce i odliczanie do startu.'
)
DESCRIPTION_CITY = (
    'Najbliższe imprezy i praktisy West Coast Swing w mieście {city} '
    '— data, miejsce i odliczanie do startu.'
)
DESCRIPTION_CALENDAR = (
    'Kalendarz wydarzeń West Coast Swing — pełna lista imprez i praktisów, '
    'do subskrybowania w telefonie.'
)
DESCRIPTION_CALENDAR_CITY = (
    'Kalendarz wydarzeń West Coast Swing w mieście {city} — pełna lista '
    'imprez i praktisów, do subskrybowania w telefonie.'
)
# The map of cities on the apex. The count comes from the database, so a new
# city in the admin panel reaches search results without a deployment.
DESCRIPTION_HUB = (
    'Imprezy i praktisy West Coast Swing w {count} miastach w Polsce '
    '— kiedy, gdzie i ile zostało do startu.'
)

# The link preview image lives with the static pages on app.gdzienawesta.com,
# which is where the generator that produces it deploys to. Referenced without
# the ?v= stamp those pages carry: this file cannot know the stamp, and every
# preview consumer caches by URL anyway, so the stamp would buy nothing here.
OG_IMAGE = 'https://app.gdzienawesta.com/og-image.png'
OG_IMAGE_ALT = 'Gdzie na Westa? — Wydarzenia West Coast Swing w Polsce'

# Where the map page takes the list of cities written in by the server, so a
# crawler that never runs our JavaScript still finds a link to every city.
CITY_LIST_MARKER = '<!-- cities:list -->'

TITLE_TAG = re.compile(r'<title>.*?</title>', re.S)
DESCRIPTION_TAG = re.compile(r'<meta name="description" content="[^"]*">')
HEAD_END = '</head>'

_cache = {}


def _read(name: str) -> str:
    """The page as it is on disk right now, remembered until it changes.

    The mtime check is not an optimisation: post-deploy.sh and stamp-assets.py
    rewrite these files after every deployment, and a copy held from before
    that would serve a page with no analytics and stale asset addresses.
    """
    path = FRONTEND_DIR / name
    stamp = path.stat().st_mtime_ns
    cached = _cache.get(name)
    if cached is None or cached[0] != stamp:
        _cache[name] = (stamp, path.read_text(encoding='utf-8'))
    return _cache[name][1]


def _escape(value: str) -> str:
    """Enough for an attribute and a text node. City names come from the admin
    panel, so they are not hostile input, but they are input."""
    return (value.replace('&', '&amp;').replace('<', '&lt;')
                 .replace('>', '&gt;').replace('"', '&quot;'))


def _preview_tags(url, title, description):
    """The canonical address and the link preview, as one block for <head>.

    The same tag set the static pages carry, so a link shared from either
    property previews the same way. Title and description are the ones the
    page was given, which means a link to a city subdomain names that city -
    the whole reason these are built here and not injected by the edge, which
    does not know the cities and must not learn them: a new city is an entry
    in the admin panel, never a deployment.
    """
    return '\n    '.join([
        f'<link rel="canonical" href="{url}">',
        '<meta property="og:type" content="website">',
        f'<meta property="og:site_name" content="{SITE_TITLE}">',
        f'<meta property="og:title" content="{title}">',
        f'<meta property="og:description" content="{description}">',
        f'<meta property="og:url" content="{url}">',
        f'<meta property="og:image" content="{OG_IMAGE}">',
        '<meta property="og:image:type" content="image/png">',
        '<meta property="og:image:width" content="1200">',
        '<meta property="og:image:height" content="630">',
        f'<meta property="og:image:alt" content="{OG_IMAGE_ALT}">',
        '<meta property="og:locale" content="pl_PL">',
        '<meta name="twitter:card" content="summary_large_image">',
        f'<meta name="twitter:image" content="{OG_IMAGE}">',
        f'<meta name="twitter:image:alt" content="{OG_IMAGE_ALT}">',
    ])


def _render(filename, title, description, head_tags):
    """The file on disk with its title, description and extra <head> tags."""
    page = _read(filename)
    title = _escape(title)
    description = _escape(description)
    page = TITLE_TAG.sub(lambda _: f'<title>{title}</title>', page, count=1)
    page = DESCRIPTION_TAG.sub(
        lambda _: f'<meta name="description" content="{description}">',
        page, count=1)
    return page.replace(HEAD_END, f'    {head_tags(title, description)}\n{HEAD_END}', 1)


class DocumentView(View):
    """Base for a city's two pages. Subclasses say which file and how to title it."""

    filename = ''

    def title_for(self, city, city_count):
        raise NotImplementedError

    def description_for(self, city, city_count):
        raise NotImplementedError

    # The address this page keeps, whichever spelling the visitor arrived
    # through. /calendar and /kalendarz are one page; the default city's
    # pages on the apex and www are its pages on its own subdomain.
    canonical_path = '/'

    def get(self, request):
        city = getattr(request, 'city', None)

        elsewhere = canonical_host(request.get_host(), city,
                                   settings.CITY_BASE_DOMAINS)
        if elsewhere:
            return HttpResponseRedirect(
                f'{scheme_for(request.get_host())}://{elsewhere}{self.canonical_path}',
                status=REDIRECT_STATUS)

        # One city means the name adds nothing - the site is about that city
        # and says so. This is the rule app.js already follows through
        # namedCity, and the two must agree or the title changes under the
        # reader a moment after the page appears.
        city_count = City.objects.filter(is_active=True).count()

        # Written here rather than into the file: one static document serves
        # every city, so a fixed canonical would point Łódź and Kraków at one
        # address. It used to be set by app.js, which meant a crawler saw it
        # only if it ran our JavaScript.
        #
        # A host naming no city we serve gets noindex instead. That page is an
        # apology with a way to the cities that do exist - worth showing to
        # the person who typed the address, worth nothing in a search result,
        # and there is no honest canonical for it to point at. Its sitemap
        # already answers 404 for the same reason.
        if city is None:
            def head_tags(title, description):
                return '<meta name="robots" content="noindex">'
        else:
            host = request.get_host()
            url = f'{scheme_for(host)}://{host}{self.canonical_path}'

            def head_tags(title, description):
                return _preview_tags(url, title, description)

        page = _render(self.filename,
                       self.title_for(city, city_count),
                       self.description_for(city, city_count),
                       head_tags)
        return HttpResponse(page, content_type='text/html; charset=utf-8')


class HomeView(DocumentView):
    """A city's page of upcoming events - or, on the apex, the map of cities."""

    filename = 'index.html'

    def get(self, request):
        host = request.get_host()
        apex = hub_host(host, settings.CITY_BASE_DOMAINS)
        if apex is None:
            return super().get(request)
        # www is the same page under a name we do not publish.
        if _hostname(host) != apex:
            return HttpResponseRedirect(f'{scheme_for(host)}://{apex}/',
                                        status=REDIRECT_STATUS)
        return _hub(request, apex)

    def title_for(self, city, city_count):
        if city is None or city_count < 2:
            return SITE_TITLE
        return f'{SITE_TITLE} - {city.name}'

    def description_for(self, city, city_count):
        if city is None or city_count < 2:
            return DESCRIPTION
        return DESCRIPTION_CITY.format(city=city.name)


class CalendarPageView(DocumentView):
    filename = 'calendar.html'
    canonical_path = '/kalendarz'

    def title_for(self, city, city_count):
        base = f'{SITE_TITLE} - {CALENDAR_TITLE}'
        # calendar.js names the city whenever it knows one, without the
        # "more than one city" rule the home page uses. Matching it here
        # rather than tidying the difference away: the page that shows the
        # title is the one that decides what it says.
        return f'{base} - {city.name}' if city is not None else base

    def description_for(self, city, city_count):
        if city is None:
            return DESCRIPTION_CALENDAR
        return DESCRIPTION_CALENDAR_CITY.format(city=city.name)


def _hub(request, apex):
    """The map of cities on the apex: cities.html with the list written in.

    The list is the page's index, and the map only draws it, so it has to be
    there without JavaScript: until now the subdomains were linked from nowhere
    in the served HTML - the footer is built by a script - and a crawler found
    them only through the sitemap.
    """
    cities = list(City.objects.filter(is_active=True))
    scheme = scheme_for(request.get_host())
    items = '\n'.join(_hub_row(city, f'{scheme}://{city.slug}.{apex}/') for city in cities)
    # One city is not a map worth counting.
    description = (DESCRIPTION_HUB.format(count=len(cities))
                   if len(cities) > 1 else DESCRIPTION)
    url = f'{scheme}://{apex}/'

    page = _render('cities.html', SITE_TITLE, description,
                   lambda title, description: _preview_tags(url, title, description))
    page = page.replace(CITY_LIST_MARKER, items, 1)
    return HttpResponse(page, content_type='text/html; charset=utf-8')


def _hub_row(city, url):
    """One row of the list: a link with the city's name, and in data-* what
    hub.js needs to put it on the map - no second request for the list."""
    name = _escape(city.name)
    coordinates = (
        f' data-lat="{city.latitude}" data-lon="{city.longitude}"'
        if city.latitude is not None and city.longitude is not None else ''
    )
    return (
        f'<a class="crow" href="{url}" data-slug="{city.slug}" data-name="{name}"{coordinates}>'
        f'<span class="tt"><b>{name}</b></span>'
        '<span class="chev"><svg class="i"><use href="#i-chev-r"/></svg></span></a>'
    )
