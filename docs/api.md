# API

Every endpoint is scoped to the city resolved from the request's `Host` header
(see `events/middleware.py`). The same path returns different events depending
on the subdomain it was asked on.

Times are ISO 8601 with a UTC offset; the frontend renders them in the
visitor's own timezone.

Every endpoint that needs a calendar reads the same cached copy of it,
the one the subscription feed hands out. Requests to Google all leave from the
server's single address, so without that the site's traffic to Google grew
with its own popularity: one fetch per visit, plus one per open tab every five
minutes. Now it is one fetch per calendar every 15 minutes no matter how busy
the site is - at the price of a calendar edit taking that long to show up.

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

## GET /api/calendar/

What the calendar page needs about the city it is showing: `city`
(`name`, `slug`), `calendar_id`, `timezone` and `google_url` — the address of
this calendar on Google, still worth offering as a link.

## GET /kalendarz.ics, /calendar.ics

This city's calendar as an iCal feed, `text/calendar`, for anyone subscribing
in their own calendar app. Both spellings serve the same thing.

The body is Google's own feed passed through, cached for 15 minutes: every
subscribed calendar app polls on its own schedule, and without the cache each
poll would become a request to Google. The last good copy is kept for a week
and answered with when Google is unreachable — a feed that is stale by minutes
goes unnoticed, while a feed that is briefly missing empties someone's
calendar. A stale answer carries `X-Feed-Stale: 1`.

`502` means we have no copy at all, fresh or stale. It is deliberately not an
empty calendar, which a subscriber's app would read as every event having been
cancelled.

`/kalendarz` and `/calendar` (without the extension) are the human page and
never reach Django — nginx serves them from the frontend.

## Errors

| Status | `error` | Meaning |
|---|---|---|
| 404 | `Unknown city` | The host names a city that does not exist or is inactive |
| 404 | `No active cities` | No city is configured at all — add one in the admin panel |
| 404 | `No upcoming events` | The city exists but its calendar has nothing ahead |
| 500 | `Server error` | Upstream calendar failure or a bug; details in `message` |

`Unknown city` and `No active cities` are deliberately distinct: only the
second one is something the site owner can fix in the admin panel.
