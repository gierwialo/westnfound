from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any
import requests
import logging
from icalendar import Calendar
from dateutil import parser
from django.utils import timezone as django_timezone
import recurring_ical_events

logger = logging.getLogger(__name__)


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
            # Use public iCal feed - no authentication needed!
            ical_url = f"https://calendar.google.com/calendar/ical/{calendar_id}/public/basic.ics"

            response = requests.get(ical_url, timeout=10)

            if response.status_code != 200:
                logger.error(f"Failed to fetch calendar {calendar_id}: {response.status_code}")
                return None

            # Parse iCal data
            cal = Calendar.from_ical(response.content)

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
                            'title': str(component.get('summary', 'Bez tytułu')),
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
                # Use public iCal feed
                ical_url = f"https://calendar.google.com/calendar/ical/{calendar_id}/public/basic.ics"
                response = requests.get(ical_url, timeout=10)

                if response.status_code != 200:
                    logger.error(f"Failed to fetch calendar {calendar_id}: {response.status_code}")
                    continue

                # Parse iCal data
                cal = Calendar.from_ical(response.content)
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
                                'title': str(component.get('summary', 'Bez tytułu')),
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
