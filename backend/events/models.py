from django.db import models


class Calendar(models.Model):
    """Model for storing Google Calendar IDs"""
    name = models.CharField(max_length=200, help_text="Nazwa kalendarza (np. 'Warsaw Westies Dance')")
    calendar_id = models.CharField(
        max_length=200,
        unique=True,
        help_text="ID kalendarza Google (np. 'warsawwestiesdance@gmail.com')"
    )
    is_active = models.BooleanField(default=True, help_text="Czy kalendarz jest aktywny")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Kalendarz"
        verbose_name_plural = "Kalendarze"
        ordering = ['name']

    def __str__(self):
        return self.name
