# West Coast Swing Event Finder 🎵

Shows what is on next for dancers in a given city, straight from a public
Google Calendar. Runs at [gdzienawesta.com](https://gdzienawesta.com).

**z miłości do Westa❤️**

## What it does

- **One city per subdomain.** The bare domain serves the default city;
  `<city>.example.com` serves that city's events. An address that names no
  configured city says so and lists the ones that exist.
- **The next three events**, swipeable, with a live countdown and buttons to
  add the event to a calendar or navigate to the venue.
- **`/kalendarz` and `/calendar`** send you to the current city's Google
  Calendar, so you can subscribe to it in your own.
- **Polish and English**, detected from the browser and switchable, with a
  preference remembered between visits.
- **Times in the visitor's own timezone**, wherever they are.
- **Cities are added in the admin panel**, not by a deploy.

## How it works

No Google API keys and no OAuth: events come from each calendar's **public
iCal feed** (`calendar.google.com/calendar/ical/<id>/public/basic.ics`), which
is parsed server-side with `icalendar` + `recurring_ical_events` so recurring
events, cancellations and per-occurrence changes all land correctly.

Which city a request is for is decided from the `Host` header
(`events/middleware.py`); an unrecognised host falls back to the default city,
so hitting the server directly behaves the same as the bare domain.

| Layer | Stack |
|---|---|
| Backend | Django 5, SQLite |
| Frontend | HTML + Alpine.js + CSS, no build step and no Node.js |
| Deploy | Docker Compose, nginx in front |

## Quick start

Requires Docker and Docker Compose.

```bash
git clone https://github.com/gierwialo/westnfound.git
cd westnfound
cp .env.example .env          # optional: ports, admin URL, secret key

docker compose --profile prod up -d
docker exec -it westnfound_backend_prod python manage.py createsuperuser
```

Open the admin panel at `http://localhost/admin/` and add your first city:

| Field | Meaning |
|---|---|
| **Name** | City name as displayed, diacritics and all |
| **Slug** | Subdomain label, ASCII, used as `<slug>.example.com`. Filled in from the name; **changing it breaks every link already shared** |
| **Calendar ID** | From Google Calendar → Settings → Integrate calendar |
| **Is default** | The city served on the bare domain. Exactly one city has this |
| **Is active** | Uncheck to hide a city without deleting it |

The site is then at `http://localhost/`.

For a development server with auto-reload and the backend port exposed, use
`--profile dev` instead and see [docs/deployment.md](docs/deployment.md).

## Subdomains

Serving `<city>.example.com` needs a wildcard DNS record, a certificate
covering it, and the base domain listed in `CITY_BASE_DOMAINS`. Subdomains can
be exercised locally without touching `/etc/hosts` — see
[docs/deployment.md](docs/deployment.md).

## Project structure

```
├── docker-compose.yml
├── backend/
│   ├── events/
│   │   ├── models.py       # City: name, slug, calendar id, default flag
│   │   ├── middleware.py   # Host header -> city
│   │   ├── services.py     # iCal fetching and recurrence expansion
│   │   ├── views.py        # API endpoints and calendar redirects
│   │   ├── slugs.py        # city name -> ASCII subdomain label
│   │   └── tests.py
│   └── westnfound/         # Django settings and URLs
├── frontend/
│   ├── index.html
│   ├── app.js              # Alpine.js logic
│   ├── translations.js     # PL/EN strings
│   ├── styles.css
│   ├── nginx.dev.conf
│   └── nginx.prod.conf
└── scripts/
    └── stamp-assets.py     # cache-busting version stamps for CSS and JS
```

## Tests

```bash
docker exec -it westnfound_backend_prod python manage.py test events
```

## Documentation

- [docs/deployment.md](docs/deployment.md) — profiles, configuration, deploying an update, troubleshooting
- [docs/api.md](docs/api.md) — endpoint reference
- [SECURITY.md](SECURITY.md) — reporting a vulnerability

## Contributing

Have an idea or found a problem? [Open an issue](https://github.com/gierwialo/westnfound/issues).

## License

MIT
