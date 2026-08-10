#!/usr/bin/env python3
"""Stamp the frontend asset links in index.html with a content hash.

nginx serves CSS and JS with `expires 1y` and `Cache-Control: immutable`,
while the HTML document is not cached at all. Without a version in the asset
URLs a returning visitor gets the new index.html together with last year's
app.js - a page whose markup refers to state and translation keys its own
script has never heard of.

The version is a hash of the file's contents, not a timestamp, so a deploy
that does not touch app.js leaves its URL alone and visitors keep their
cached copy.

Run from the repository root, after any step that edits index.html:

    python3 scripts/stamp-assets.py

Re-running is safe: an existing ?v= is replaced, not appended to.
"""

import hashlib
import re
import sys
from pathlib import Path

ASSETS = ('styles.css', 'app.js', 'translations.js')


def content_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()[:8]


def stamp(frontend: Path) -> list[str]:
    index = frontend / 'index.html'
    html = index.read_text(encoding='utf-8')
    stamped = []

    for asset in ASSETS:
        asset_path = frontend / asset
        if not asset_path.exists():
            print(f'skipping {asset}: not found', file=sys.stderr)
            continue

        version = content_hash(asset_path)
        # Matches href="styles.css" and href="styles.css?v=old" alike, in
        # either quote style, and leaves any other attribute untouched.
        pattern = re.compile(
            r'(["\'])' + re.escape(asset) + r'(?:\?v=[^"\']*)?\1'
        )
        html, count = pattern.subn(rf'\g<1>{asset}?v={version}\g<1>', html)
        if count:
            stamped.append(f'{asset} -> {version} ({count}x)')
        else:
            print(f'warning: no reference to {asset} in index.html', file=sys.stderr)

    index.write_text(html, encoding='utf-8')
    return stamped


def main() -> int:
    frontend = Path(__file__).resolve().parent.parent / 'frontend'
    if not (frontend / 'index.html').exists():
        print(f'error: {frontend}/index.html not found', file=sys.stderr)
        return 1

    for line in stamp(frontend):
        print(line)
    return 0


if __name__ == '__main__':
    sys.exit(main())
