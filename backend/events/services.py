from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any, Tuple
from urllib.parse import quote
import requests
import logging
from django.core.cache import cache
from icalendar import Calendar
from dateutil import parser
from django.utils import timezone as django_timezone
import recurring_ical_events

logger = logging.getLogger(__name__)


def ical_url(calendar_id: str) -> str:
    """The public iCal feed of a Google calendar.

    One place builds this address, because three things now depend on its
    exact shape: the two event endpoints, and the feed we hand to people
    subscribing at gdzienawesta.com.
    """
    return (
        'https://calendar.google.com/calendar/ical/'
        f'{quote(calendar_id, safe="")}/public/basic.ics'
    )


class CalendarFeedService:
    """Google's iCal feed for a city, cached, for handing on to subscribers.

    Standing between a subscriber and Google is a promise: a calendar app that
    subscribed to gdzienawesta.com asks us, not Google, so when we answer
    badly its owner sees an empty week. Two things keep that promise.

    The fresh copy spares Google the polling. Every subscribed calendar app
    refreshes on its own schedule, and without a cache each one of them would
    become a request to Google; with it, they share one fetch per quarter of
    an hour, which is far more often than a dance calendar changes.

    The last good copy answers when Google does not. A feed that is minutes
    stale is a calendar nobody notices; a feed that is briefly missing is
    events disappearing from someone's phone.
    """

    FRESH_SECONDS = 15 * 60
    LAST_GOOD_SECONDS = 7 * 24 * 60 * 60
    TIMEOUT_SECONDS = 10

    def get(self, calendar_id: str) -> Tuple[Optional[bytes], bool]:
        """Return (feed, is_stale). ``feed`` is None only if we never had one."""
        fresh_key = f'ics:fresh:{calendar_id}'
        last_good_key = f'ics:last-good:{calendar_id}'

        cached = cache.get(fresh_key)
        if cached is not None:
            return cached, False

        body = self._fetch(calendar_id)
        if body is not None:
            cache.set(fresh_key, body, self.FRESH_SECONDS)
            cache.set(last_good_key, body, self.LAST_GOOD_SECONDS)
            return body, False

        last_good = cache.get(last_good_key)
        if last_good is not None:
            logger.warning(
                f'Serving a stale feed for {calendar_id}: Google is unreachable'
            )
            return last_good, True

        return None, False

    def _fetch(self, calendar_id: str) -> Optional[bytes]:
        try:
            response = requests.get(ical_url(calendar_id), timeout=self.TIMEOUT_SECONDS)
        except requests.RequestException as exc:
            logger.error(f'Failed to fetch feed {calendar_id}: {exc}')
            return None

        if response.status_code != 200:
            logger.error(
                f'Failed to fetch feed {calendar_id}: {response.status_code}'
            )
            return None

        # A calendar Google has stopped publishing answers 200 with a login
        # page. Handing that to a subscriber would replace their events with
        # HTML, and caching it would keep doing so for a week.
        if not response.content.lstrip().startswith(b'BEGIN:VCALENDAR'):
            logger.error(f'Feed {calendar_id} did not come back as a calendar')
            return None

        return response.content


class GoogleCalendarService:
    """Service for fetching events from Google Calendar using public iCal feed"""

    def get_next_event(self, calendar_id: str) -> Optional[Dict[str, Any]]:
        """
        Fetch the next upcoming event from a Google Calendar using iCal feed

        Args:
            calendar_id: Google Calendar ID

        Returns:
            Dictionary with event data or None if no events found
        """
        try:
            # The same cached copy the subscription feed hands out. Without it
            # every visit to the site was its own request to Google, from the
            # server's single address; now the whole site, every visitor and
            # every subscriber share one fetch per calendar per quarter hour.
            feed, _ = CalendarFeedService().get(calendar_id)

            if feed is None:
                logger.error(f"Failed to fetch calendar {calendar_id}")
                return None

            # Parse iCal data
            cal = Calendar.from_ical(feed)

            # Use Django's configured timezone (from settings.TIME_ZONE)
            now = django_timezone.now()

            # Get all events (including recurring) for the next year
            # recurring_ical_events expands RRULE to individual occurrences
            events = recurring_ical_events.of(cal).between(
                now,
                now + timedelta(days=365)
            )

            upcoming_events = []

            for component in events:
                if component.name == "VEVENT":
                    dtstart = component.get('dtstart')
                    if not dtstart:
                        continue

                    # Get start datetime
                    start_dt = dtstart.dt

                    # Convert to datetime if it's a date
                    if isinstance(start_dt, datetime):
                        # Ensure timezone awareness
                        if start_dt.tzinfo is None:
                            start_dt = django_timezone.make_aware(start_dt)
                    else:
                        # It's a date, convert to datetime at midnight
                        from datetime import date, time
                        start_dt = django_timezone.make_aware(datetime.combine(start_dt, time.min))

                    # Get end datetime
                    dtend = component.get('dtend')
                    end_dt = None
                    if dtend:
                        end_dt = dtend.dt
                        if isinstance(end_dt, datetime):
                            if end_dt.tzinfo is None:
                                end_dt = django_timezone.make_aware(end_dt)
                        else:
                            from datetime import time
                            end_dt = django_timezone.make_aware(datetime.combine(end_dt, time.min))

                    # Skip events longer than 12 hours
                    if end_dt:
                        duration = end_dt - start_dt
                        if duration > timedelta(hours=12):
                            continue

                    # Show events that haven't ended yet (not just future events)
                    # Use end time if available, otherwise use start time
                    event_time = end_dt if end_dt else start_dt
                    if event_time > now:
                        event_data = {
                            'title': str(component.get('summary', 'Untitled')),
                            'description': str(component.get('description', '')),
                            'location': str(component.get('location', '')),
                            'start': start_dt.isoformat(),
                            'end': end_dt.isoformat() if end_dt else start_dt.isoformat(),
                            'start_dt': start_dt,  # For sorting
                            'calendar_id': calendar_id,
                        }
                        upcoming_events.append(event_data)

            if not upcoming_events:
                return None

            # Sort by start time and return the earliest
            upcoming_events.sort(key=lambda x: x['start_dt'])
            next_event = upcoming_events[0]

            # Remove the helper field
            del next_event['start_dt']

            return next_event

        except Exception as e:
            logger.error(f"Error fetching events from calendar {calendar_id}: {str(e)}", exc_info=True)
            return None

    def get_next_event_from_multiple_calendars(self, calendar_ids: list) -> Optional[Dict[str, Any]]:
        """
        Fetch the next upcoming event from multiple calendars

        Args:
            calendar_ids: List of Google Calendar IDs

        Returns:
            Dictionary with the nearest event data or None if no events found
        """
        all_events = []

        for calendar_id in calendar_ids:
            event = self.get_next_event(calendar_id)
            if event:
                all_events.append(event)

        if not all_events:
            return None

        # Sort by start time and return the earliest event
        all_events.sort(key=lambda x: x['start'])
        return all_events[0]

    def get_next_events_from_multiple_calendars(self, calendar_ids: list, limit: int = 3) -> list:
        """
        Fetch the next N upcoming events from multiple calendars

        Args:
            calendar_ids: List of Google Calendar IDs
            limit: Number of events to return (default: 3)

        Returns:
            List of event dictionaries sorted by start time
        """
        all_events = []

        for calendar_id in calendar_ids:
            try:
                # Shared with the subscription feed; see get_next_event().
                feed, _ = CalendarFeedService().get(calendar_id)

                if feed is None:
                    logger.error(f"Failed to fetch calendar {calendar_id}")
                    continue

                # Parse iCal data
                cal = Calendar.from_ical(feed)
                now = django_timezone.now()

                # Get all events for the next year
                events = recurring_ical_events.of(cal).between(
                    now,
                    now + timedelta(days=365)
                )

                for component in events:
                    if component.name == "VEVENT":
                        dtstart = component.get('dtstart')
                        if not dtstart:
                            continue

                        # Get start datetime
                        start_dt = dtstart.dt

                        # Convert to datetime if it's a date
                        if isinstance(start_dt, datetime):
                            if start_dt.tzinfo is None:
                                start_dt = django_timezone.make_aware(start_dt)
                        else:
                            from datetime import date, time
                            start_dt = django_timezone.make_aware(datetime.combine(start_dt, time.min))

                        # Get end datetime
                        dtend = component.get('dtend')
                        end_dt = None
                        if dtend:
                            end_dt = dtend.dt
                            if isinstance(end_dt, datetime):
                                if end_dt.tzinfo is None:
                                    end_dt = django_timezone.make_aware(end_dt)
                            else:
                                from datetime import time
                                end_dt = django_timezone.make_aware(datetime.combine(end_dt, time.min))

                        # Skip events longer than 12 hours
                        if end_dt:
                            duration = end_dt - start_dt
                            if duration > timedelta(hours=12):
                                continue

                        # Show events that haven't ended yet
                        event_time = end_dt if end_dt else start_dt
                        if event_time > now:
                            event_data = {
                                'title': str(component.get('summary', 'Untitled')),
                                'description': str(component.get('description', '')),
                                'location': str(component.get('location', '')),
                                'start': start_dt.isoformat(),
                                'end': end_dt.isoformat() if end_dt else start_dt.isoformat(),
                                'start_dt': start_dt,  # For sorting
                                'calendar_id': calendar_id,
                            }
                            all_events.append(event_data)

            except Exception as e:
                logger.error(f"Error fetching events from calendar {calendar_id}: {str(e)}", exc_info=True)
                continue

        if not all_events:
            return []

        # Sort by start time
        all_events.sort(key=lambda x: x['start_dt'])

        # Get the first N events
        result_events = all_events[:limit]

        # Remove the helper field
        for event in result_events:
            del event['start_dt']

        return result_events
