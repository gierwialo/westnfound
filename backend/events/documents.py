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

from django.http import HttpResponse
from django.views import View

from .models import City

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

TITLE_TAG = re.compile(r'<title>.*?</title>', re.S)
DESCRIPTION_TAG = re.compile(r'<meta name="description" content="[^"]*">')

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

    def get(self, request):
        city = getattr(request, 'city', None)
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
