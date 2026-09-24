from django import forms
from django.contrib import admin

from .coordinates import format_coordinates, parse_coordinates
from .models import City


class CityForm(forms.ModelForm):
    # One field in place of latitude and longitude: see events/coordinates.py.
    coordinates = forms.CharField(
        required=False,
        help_text="Where the city sits on the map on gdzienawesta.com. In Google Maps, "
                  "right-click the city centre and click the numbers at the top of the "
                  "menu: that copies them in this format, latitude first. Leave empty "
                  "to list the city without a dot on the map.",
        widget=forms.TextInput(attrs={'placeholder': '50.0412, 21.9991'}),
    )

    class Meta:
        model = City
        fields = ['name', 'slug', 'calendar_id', 'is_default', 'is_active']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk:
            self.initial['coordinates'] = format_coordinates(
                self.instance.latitude, self.instance.longitude
            )

    def clean_coordinates(self):
        return parse_coordinates(self.cleaned_data['coordinates'])

    def _post_clean(self):
        # Before the model's own clean() runs, so it sees the pair it will save.
        self.instance.latitude, self.instance.longitude = (
            self.cleaned_data.get('coordinates') or (None, None)
        )
        super()._post_clean()


@admin.register(City)
class CityAdmin(admin.ModelAdmin):
    form = CityForm
    fields = ['name', 'slug', 'calendar_id', 'coordinates', 'is_default', 'is_active']
    list_display = ['name', 'slug', 'calendar_id', 'on_map', 'is_default', 'is_active', 'created_at']
    list_filter = ['is_active', 'is_default', 'created_at']
    search_fields = ['name', 'slug', 'calendar_id']
    list_editable = ['is_active']
    # Django's urlify.js carries a Polish map, so the browser fills in the same
    # value City.save() would - see events/slugs.py for why the stroked L needs
    # special handling. The field stays editable: once a city has been shared,
    # its subdomain must survive a rename of the city.
    prepopulated_fields = {'slug': ('name',)}

    @admin.display(boolean=True, description='On map')
    def on_map(self, city):
        return city.latitude is not None
