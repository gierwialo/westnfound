# Deployment

## Profiles

Two Compose profiles, differing in how the backend runs and whether its port
is reachable from outside.

| | `dev` | `prod` |
|---|---|---|
| Backend | Django dev server, auto-reload | Gunicorn, 4 workers |
| Backend port | Published (`BACKEND_PORT`, default 8000) | Internal only |
| `DEBUG` | True | False |
| Security headers | No | Yes |
| Health endpoint | No | `GET /health` |

```bash
docker compose --profile prod up -d          # or --profile dev
FRONTEND_PORT=3000 docker compose --profile prod up -d
```

Container names carry the profile: `westnfound_backend_prod`,
`westnfound_frontend_dev`, and so on.

## Configuration

Copy `.env.example` to `.env` and adjust. Everything is read from the
environment; nothing needs editing in `settings.py`.

| Variable | Purpose |
|---|---|
| `DJANGO_SECRET_KEY` | **Change it for anything public.** |
| `DEBUG` | `False` in production. |
| `ALLOWED_HOSTS` | Comma-separated. With subdomains, a leading dot covers them all: `.example.com`. |
| `CSRF_TRUSTED_ORIGINS` | Required behind a reverse proxy, or admin logins fail. Include the scheme: `https://example.com`. |
| `CITY_BASE_DOMAINS` | Domains under which a subdomain names a city. Default `gdzienawesta.com,lvh.me,localhost`. |
| `DJANGO_ADMIN_URL` | Moves the admin panel off `/admin/`. |
| `FRONTEND_PORT`, `BACKEND_PORT` | Published ports. |
| `FRONTEND_BIND_IPV4`, `FRONTEND_BIND_IPV6` | Bind addresses. Useful when another proxy already owns the public port — bind the frontend to loopback and let that proxy reach it. |

`GOOGLE_CALENDAR_API_KEY` is a leftover: public iCal feeds need no key and
nothing reads this variable.

### Moving the admin panel

```bash
DJANGO_ADMIN_URL=my-secret-panel-xyz123
```

The production nginx config proxies any single-segment path with a trailing
slash to Django, except `/api/`, `/static/` and `/health`, so a custom admin
URL works whatever you call it. The trailing slash is what keeps this rule off
the frontend: `/app.js` and `/styles.css` sit at the top level and never match
it. A frontend file in a subdirectory would, though — so keep them flat, or
add its directory to the exclusion list.

This only makes the panel harder to find. It is not access control — use a
strong password.

## Subdomains

`<city>.example.com` needs:

1. A wildcard DNS record `*` pointing where the bare domain points.
2. A certificate covering `*.example.com` — a one-level wildcard, which
   Let's Encrypt and Cloudflare Universal SSL both issue.
3. `CITY_BASE_DOMAINS` containing `example.com`.
4. `ALLOWED_HOSTS` containing `.example.com`.

A host matching none of the base domains resolves to the default city, so
direct hits on the server's address and health checks behave as they did
before cities existed.

## Deploying an update

```bash
git pull
docker compose --profile prod up -d --build
python3 scripts/stamp-assets.py
```

`stamp-assets.py` rewrites the asset links in every page under `frontend/`
with a hash of each file's contents. **It is not optional.** nginx serves CSS and JS with
`expires 1y` and `Cache-Control: immutable`, while the HTML document is not
cached — so without it a returning visitor gets new markup with last year's
JavaScript. Because the version is a content hash, files you did not touch
keep their URLs and stay cached.

Re-running the script is safe; an existing `?v=` is replaced, not appended to.

If your deployment injects anything into the pages after checkout —
analytics, for instance, from a script kept out of the repository — run it in
the same step. Order does not matter. Such a script wants checking whenever a
page is added: one written when `index.html` was the only page will silently
skip the new one.

## Management

```bash
docker compose logs -f                    # everything
docker compose logs -f backend-prod       # one service
docker compose restart
docker compose down
```

## Troubleshooting

**No events showing.** Check the calendar ID, that the calendar is shared
publicly **with full details** rather than free/busy only, and that it has
something upcoming. `docker compose logs backend-prod` shows fetch failures.

**A subdomain shows "no such city".** The slug in the admin panel must match
the subdomain label exactly, the city must be active, and `CITY_BASE_DOMAINS`
must contain the base domain. Nested names like `a.b.example.com` are not
city addresses.

**Admin login fails with a CSRF error.** `CSRF_TRUSTED_ORIGINS` is missing the
origin you are using, scheme included.

**`DisallowedHost`.** Add the domain to `ALLOWED_HOSTS`; with subdomains use
the leading-dot form.

**Port already in use.** Change `FRONTEND_PORT` / `BACKEND_PORT`, or bind the
frontend to loopback with `FRONTEND_BIND_IPV4` / `FRONTEND_BIND_IPV6` and put
your existing proxy in front.

**Times look wrong.** They are rendered in the visitor's timezone, not the
server's. Check `TIME_ZONE` only if a calendar's own timezone is unset.
