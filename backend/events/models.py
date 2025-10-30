from django.db import models


class Calendar(models.Model):
    """Model for storing Google Calendar IDs"""
    name = models.CharField(max_length=200, help_text="Calendar name (e.g. 'Warsaw Westies Dance')")
    calendar_id = models.CharField(
        max_length=200,
        unique=True,
        help_text="Google Calendar ID (e.g. 'warsawwestiesdance@gmail.com')"
    )
    is_active = models.BooleanField(default=True, help_text="Whether the calendar is active")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Calendar"
        verbose_name_plural = "Calendars"
        ordering = ['name']

    def __str__(self):
        return self.name
