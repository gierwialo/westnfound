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

from .middleware import canonical_host, scheme_for
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
DESCRIPTION = (
    'Najbliższe imprezy i warsztaty West Coast Swing '
    '— data, miejsce i odliczanie do startu.'
)
DESCRIPTION_CITY = (
    'Najbliższe imprezy i warsztaty West Coast Swing w mieście {city} '
    '— data, miejsce i odliczanie do startu.'
)
DESCRIPTION_CALENDAR = (
    'Kalendarz wydarzeń West Coast Swing — pełna lista imprez i warsztatów, '
    'do subskrybowania w telefonie.'
)
DESCRIPTION_CALENDAR_CITY = (
    'Kalendarz wydarzeń West Coast Swing w mieście {city} — pełna lista '
    'imprez i warsztatów, do subskrybowania w telefonie.'
)

# The link preview image lives with the static pages on app.gdzienawesta.com,
# which is where the generator that produces it deploys to. Referenced without
# the ?v= stamp those pages carry: this file cannot know the stamp, and every
# preview consumer caches by URL anyway, so the stamp would buy nothing here.
OG_IMAGE = 'https://app.gdzienawesta.com/og-image.png'
OG_IMAGE_ALT = 'Gdzie Na Westa? — Wydarzenia West Coast Swing w Polsce'

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


class DocumentView(View):
    """Base for the two pages. Subclasses say which file and how to title it."""

    filename = ''

    def title_for(self, city, city_count):
        raise NotImplementedError

    def description_for(self, city, city_count):
        raise NotImplementedError

    # The address this page keeps, whichever spelling the visitor arrived
    # through. /calendar and /kalendarz are one page; so are the apex and the
    # subdomain of the default city.
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

        page = _read(self.filename)
        title = _escape(self.title_for(city, city_count))
        description = _escape(self.description_for(city, city_count))

        page = TITLE_TAG.sub(lambda _: f'<title>{title}</title>', page, count=1)
        page = DESCRIPTION_TAG.sub(
            lambda _: f'<meta name="description" content="{description}">',
            page, count=1)

        # Written here rather than into the file: one static document serves
        # every city, so a fixed canonical would point Łódź and Kraków at the
        # apex. It used to be set by app.js, which meant a crawler saw it only
        # if it ran our JavaScript.
        #
        # A host naming no city we serve gets noindex instead. That page is an
        # apology with a list of the cities that do exist - worth showing to
        # the person who typed the address, worth nothing in a search result,
        # and there is no honest canonical for it to point at. Its sitemap
        # already answers 404 for the same reason.
        if city is None:
            tag = '<meta name="robots" content="noindex">'
        else:
            host = request.get_host()
            url = f'{scheme_for(host)}://{host}{self.canonical_path}'
            # The same tag set the static pages carry, so a link shared from
            # either property previews the same way. Title and description are
            # the ones computed above, which means a link to a city subdomain
            # names that city - the whole reason these are built here and not
            # injected by the edge, which does not know the cities and must not
            # learn them: a new city is an entry in the admin panel, never a
            # deployment.
            tag = '\n    '.join([
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
        page = page.replace(HEAD_END, f'    {tag}\n{HEAD_END}', 1)

        return HttpResponse(page, content_type='text/html; charset=utf-8')


class HomeView(DocumentView):
    filename = 'index.html'

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
