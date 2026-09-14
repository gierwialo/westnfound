"""
Django settings for westnfound project.
"""

from pathlib import Path
import os

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY', 'django-insecure-dev-key-change-me')

DEBUG = os.environ.get('DEBUG', 'False') == 'True'

ALLOWED_HOSTS = os.environ.get('ALLOWED_HOSTS', '*').split(',')

# CSRF settings for production with reverse proxy
CSRF_TRUSTED_ORIGINS = os.environ.get('CSRF_TRUSTED_ORIGINS', '').split(',') if os.environ.get('CSRF_TRUSTED_ORIGINS') else []

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'corsheaders',
    'events',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'events.middleware.CityMiddleware',
]

# Domains under which a subdomain names a city: lodz.gdzienawesta.com and,
# for local work, lodz.lvh.me (*.lvh.me resolves to 127.0.0.1). Any other host
# resolves to the default city, which is what the site did before cities.
CITY_BASE_DOMAINS = [
    d.strip().lower()
    for d in os.environ.get(
        'CITY_BASE_DOMAINS', 'gdzienawesta.com,lvh.me,localhost'
    ).split(',')
    if d.strip()
]

ROOT_URLCONF = 'westnfound.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'westnfound.wsgi.application'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

LANGUAGE_CODE = 'pl-pl'

TIME_ZONE = 'Europe/Warsaw'

USE_I18N = True

USE_TZ = True

STATIC_URL = 'static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Where the cached calendar feed lives. File based rather than in memory
# because gunicorn runs four workers: a per-process cache would mean four
# copies of every calendar and four times the polling of Google.
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.filebased.FileBasedCache',
        'LOCATION': os.environ.get('CACHE_DIR', '/tmp/westnfound-cache'),
    }
}

# CORS settings
CORS_ALLOW_ALL_ORIGINS = True
CORS_ALLOW_CREDENTIALS = True

# Google Calendar API (optional - for public calendars)
GOOGLE_CALENDAR_API_KEY = os.environ.get('GOOGLE_CALENDAR_API_KEY', '')


# Wsparcie kosztów projektu — jedno źródło prawdy dla strony i aplikacji.
#
# Kwoty i adres czyta `GET /api/support-info`. Dotąd żyły w dwóch miejscach:
# wpisane wprost w `support.html` i w dokumentacji. Zmiana ceny u Apple'a albo
# u rejestratora domeny to odtąd zmienna środowiskowa, a nie edycja strony.
#
# KWOTY NIE MAJĄ WARTOŚCI DOMYŚLNYCH I TO JEST CELOWE. To repozytorium jest
# publiczne, a historia gita wieczna — liczby wpisane tu jako domyślne zostałyby
# w niej na zawsze, a brain trzyma koszty projektu poza `web/` właśnie z tego
# powodu. Brak zmiennej znaczy więc "nie wiem", a nie "weź tę liczbę": endpoint
# oddaje wtedy 404, a strona pokazuje swoją kopię awaryjną.
SUPPORT_ENABLED = os.environ.get('SUPPORT_ENABLED', 'True') == 'True'

# Adres NASZEJ strony wsparcia — to on jedzie w endpoincie i na niego prowadzi
# przycisk w aplikacji. To NIE jest adres zbiórki: na Zrzutkę prowadzi dopiero
# przycisk na samej stronie, i ten adres żyje w `support.html`. Reguła
# komunikacji: podajemy zawsze naszą stronę, nigdy adres operatora wprost.
SUPPORT_PAGE_URL = os.environ.get(
    'SUPPORT_PAGE_URL', 'https://app.gdzienawesta.com/support.html'
)


def _money_from_env(name):
    """Złotówki ze zmiennej środowiskowej, albo None.

    Zepsuta wartość zachowuje się jak brak — lepiej nie oddać nic, niż oddać
    zero, bo "0 zł kosztów" to zdanie, które wygląda jak pomiar.
    """
    raw = os.environ.get(name, '').strip()
    if not raw:
        return None
    try:
        value = float(raw.replace(',', '.'))
    except ValueError:
        return None
    return value if value > 0 else None


SUPPORT_ANNUAL_COST_PLN = _money_from_env('SUPPORT_ANNUAL_COST_PLN')
SUPPORT_HISTORICAL_COST_PLN = _money_from_env('SUPPORT_HISTORICAL_COST_PLN')
