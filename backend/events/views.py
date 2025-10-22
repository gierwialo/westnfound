from django.http import JsonResponse
from django.views import View
from .models import Calendar
from .services import GoogleCalendarService
import logging

logger = logging.getLogger(__name__)


class NextEventView(View):
    """API endpoint to get the next upcoming event from all active calendars"""

    def get(self, request):
        try:
            # Get all active calendars
            active_calendars = Calendar.objects.filter(is_active=True)

            if not active_calendars.exists():
                return JsonResponse({
                    'error': 'Brak aktywnych kalendarzy',
                    'message': 'Dodaj kalendarze w panelu administracyjnym'
                }, status=404)

            # Get calendar IDs
            calendar_ids = [cal.calendar_id for cal in active_calendars]

            # Fetch next event
            service = GoogleCalendarService()
            event = service.get_next_event_from_multiple_calendars(calendar_ids)

            if not event:
                return JsonResponse({
                    'error': 'Brak nadchodzących wydarzeń',
                    'message': 'Nie znaleziono żadnych nadchodzących wydarzeń w kalendarzach'
                }, status=404)

            return JsonResponse({
                'success': True,
                'event': event
            })

        except Exception as e:
            logger.error(f"Error in NextEventView: {str(e)}")
            return JsonResponse({
                'error': 'Błąd serwera',
                'message': str(e)
            }, status=500)
