# API

Every endpoint is scoped to the city resolved from the request's `Host` header
(see `events/middleware.py`). The same path returns different events depending
on the subdomain it was asked on.

Times are ISO 8601 with a UTC offset; the frontend renders them in the
visitor's own timezone.

## GET /api/next-events/

The next few events for this city.

**Query parameters**

| Name | Default | Notes |
|---|---|---|
| `limit` | 3 | Clamped to 1–10; anything outside that, or unparseable, falls back to 3 |

**200**

```json
{
  "success": true,
  "count": 2,
  "events": [
    {
      "title": "West Friday Social",
      "description": "Weekly dance social...",
      "location": "Tango Milonga, Wybrzeże Kościuszkowskie 21A, Warszawa",
      "start": "2026-08-14T21:00:00+02:00",
      "end": "2026-08-15T00:00:00+02:00",
      "calendar_id": "warsawwestiesdance@gmail.com"
    }
  ]
}
```

## GET /api/next-event/

The single next event for this city. Same event shape, under `event`.

## GET /api/cities/

Every active city, for the footer and the unknown-city page.

```json
{
  "success": true,
  "count": 2,
  "current": "lodz",
  "cities": [
    { "name": "Łódź", "slug": "lodz", "url": "//lodz.gdzienawesta.com", "is_current": true },
    { "name": "Warszawa", "slug": "warszawa", "url": "//gdzienawesta.com", "is_current": false }
  ]
}
```

- Cities are ordered by slug. Because slugs are ASCII, that ordering matches
  Polish alphabetical order, which ordering by name would not: `Ł` sorts after
  `Z` byte-wise, so Łódź would come last.
- The default city's `url` is the bare domain; the others get their subdomain.
- URLs are protocol-relative on purpose. TLS is often terminated by a proxy,
  so the origin sees plain HTTP and would otherwise hand out `http://` links
  on an `https://` page.
- `current` is `null` when the host names no city we serve.

## GET /kalendarz, /calendar

Redirect (302) to this city's Google Calendar embed. Both spellings work, with
and without a trailing slash, and none of the four bounces through an
intermediate redirect.

## Errors

| Status | `error` | Meaning |
|---|---|---|
| 404 | `Unknown city` | The host names a city that does not exist or is inactive |
| 404 | `No active cities` | No city is configured at all — add one in the admin panel |
| 404 | `No upcoming events` | The city exists but its calendar has nothing ahead |
| 500 | `Server error` | Upstream calendar failure or a bug; details in `message` |

`Unknown city` and `No active cities` are deliberately distinct: only the
second one is something the site owner can fix in the admin panel.
