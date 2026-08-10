"""Slug generation for city subdomains.

Django's own slugify() is not usable here. It strips diacritics by NFKD
normalisation, which works for characters that decompose into a base letter
plus a combining mark (o-acute, n-acute, a-ogonek). The Polish stroked L is a
distinct letter that does not decompose, so it is simply dropped:

    slugify("Łódź")    -> "odz"
    slugify("Wrocław") -> "wrocaw"

Both would become live subdomains. The stroked L is mapped explicitly below
before normalisation runs.
"""

import re
import unicodedata

# Characters that NFKD leaves alone and that therefore need an explicit mapping.
NON_DECOMPOSING = str.maketrans({
    'ł': 'l',
    'Ł': 'L',
})

MAX_SLUG_LENGTH = 63  # single DNS label limit


def to_slug(name: str) -> str:
    """Turn a city name into an ASCII subdomain label.

    >>> to_slug("Łódź")
    'lodz'
    >>> to_slug("Zielona Góra")
    'zielona-gora'
    """
    ascii_name = unicodedata.normalize(
        'NFKD', name.translate(NON_DECOMPOSING)
    ).encode('ascii', 'ignore').decode('ascii')

    slug = re.sub(r'[^a-z0-9]+', '-', ascii_name.lower()).strip('-')
    return slug[:MAX_SLUG_LENGTH].rstrip('-')
