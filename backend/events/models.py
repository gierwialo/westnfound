from django.core.exceptions import ValidationError
from django.db import models

from .slugs import to_slug


class City(models.Model):
    """A city with its own subdomain and Google Calendar.

    One row is one city with one calendar. Cities are ordered by slug rather
    than by name: the slug is plain ASCII, so byte ordering matches Polish
    alphabetical ordering, while ordering by name would put "Łódź" after "Z".
    """
    name = models.CharField(
        max_length=200,
        help_text="City name with diacritics, as displayed (e.g. 'Łódź')"
    )
    slug = models.SlugField(
        max_length=63,
        unique=True,
        help_text="Subdomain label, ASCII only (e.g. 'lodz' for lodz.gdzienawesta.com). "
                  "Filled in from the name when left blank. Changing it breaks "
                  "every link already shared for this city."
    )
    calendar_id = models.CharField(
        max_length=200,
        unique=True,
        help_text="Google Calendar ID (e.g. 'warsawwestiesdance@gmail.com')"
    )
    is_default = models.BooleanField(
        default=False,
        help_text="City shown on gdzienawesta.com itself. Exactly one city has this."
    )
    is_active = models.BooleanField(default=True, help_text="Whether the city is active")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "City"
        verbose_name_plural = "Cities"
        ordering = ['slug']

    def __str__(self):
        return self.name

    def clean(self):
        # An inactive default city would leave the apex with nothing to show.
        if self.is_default and not self.is_active:
            raise ValidationError({
                'is_active': "The default city cannot be inactive - gdzienawesta.com "
                             "would have no events to show."
            })

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = to_slug(self.name)
        super().save(*args, **kwargs)
        # Exactly one default: promoting a city demotes whichever held the flag.
        # Done after the insert so a new default already has a primary key.
        if self.is_default:
            City.objects.filter(is_default=True).exclude(pk=self.pk).update(is_default=False)

    @classmethod
    def default(cls):
        """The city served on the apex domain, or None if the table is empty."""
        return cls.objects.filter(is_active=True, is_default=True).first()
