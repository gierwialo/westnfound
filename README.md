# West Coast Swing Event Finder 🎵

A simple web application to display the next upcoming dance event from Google Calendars.

**z miłości do Westa❤️**

## Contributing

Have an idea or found an issue? Please [open an issue](https://github.com/gierwialo/westnfound/issues) on GitHub!

## Architecture

- **Backend**: Django 5 + Google Calendar API + SQLite
- **Frontend**: HTML + Alpine.js + CSS (no Node.js!)
- **Deploy**: Docker Compose

## Features

- ✅ Support for multiple Google Calendars
- ✅ Automatic display of the next upcoming event
- ✅ Multi-language support (Polish & English)
- ✅ Automatic language detection based on browser settings
- ✅ Times displayed in user's local timezone
- ✅ Beautiful, responsive interface
- ✅ Countdown timer to the event
- ✅ Django admin panel for calendar management
- ✅ Lightweight architecture (no PostgreSQL, no Node.js)

## Quick Start

### Requirements

- Docker
- Docker Compose

### Deployment Profiles

The application supports two deployment profiles:

1. **Development (`dev`)**: Django dev server + exposed backend port
2. **Production (`prod`)**: Gunicorn + Nginx (backend not publicly accessible)

### Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd westnfound
```

2. (Optional) Configure ports in `.env`:
```bash
cp .env.example .env
# Edit .env to set FRONTEND_PORT (default: 80) and BACKEND_PORT (dev only, default: 8000)
```

3. Start the application:

**Development mode:**
```bash
docker compose --profile dev up -d
```

**Production mode (recommended):**
```bash
docker compose --profile prod up -d
```

**Custom port example:**
```bash
FRONTEND_PORT=3000 docker compose --profile prod up -d
```

4. Create Django superuser:

**Development:**
```bash
docker exec -it westnfound_backend_dev python manage.py createsuperuser
```

**Production:**
```bash
docker exec -it westnfound_backend_prod python manage.py createsuperuser
```

5. (Optional) Configure production settings in `.env`:
```bash
# Custom admin URL for security
DJANGO_ADMIN_URL=my-secret-admin-panel

# For production deployment, configure CSRF trusted origins
# This is REQUIRED when running behind a reverse proxy (Nginx)
CSRF_TRUSTED_ORIGINS=https://yourdomain.com,https://www.yourdomain.com

# Optionally restrict allowed hosts
ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com
```

6. Add calendars:
   - Open admin panel:
     - **Dev**: http://localhost:8000/admin/
     - **Prod**: http://localhost/admin/ (or your custom URL from DJANGO_ADMIN_URL)
   - Login with your superuser account
   - Add new calendars in the "Calendars" section
   - For each calendar provide:
     - **Name**: e.g., "Warsaw Westies Dance"
     - **Calendar ID**: e.g., "yourcalendar@gmail.com"
     - **Is active**: Check to enable the calendar

7. Open the application:

**Development:**
   - Frontend: http://localhost/
   - Backend API: http://localhost:8000/api/next-event/ (direct access)
   - Admin panel: http://localhost:8000/admin/

**Production:**
   - Frontend: http://localhost/
   - Backend API: http://localhost/api/next-event/ (through Nginx only)
   - Admin panel: http://localhost/admin/ (configurable via DJANGO_ADMIN_URL)
   - Health check: http://localhost/health

### Development vs Production

| Feature | Development | Production |
|---------|-------------|------------|
| Backend Server | Django dev server | Gunicorn (4 workers) |
| Backend Port | Exposed (8000) | Internal only |
| Frontend Server | Nginx | Nginx |
| API Access | Direct + through Nginx | Through Nginx only |
| DEBUG | True | False |
| Auto-reload | Yes | No |
| Security Headers | No | Yes |
| Health Endpoint | No | Yes (/health) |

## Project Structure

```
.
├── docker-compose.yml          # Docker Compose configuration
├── backend/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── manage.py
│   ├── westnfound/            # Django configuration
│   │   ├── settings.py
│   │   ├── urls.py
│   │   └── ...
│   └── events/                # Events app
│       ├── models.py          # Calendar model
│       ├── services.py        # Google Calendar API integration
│       ├── views.py           # API endpoint
│       ├── admin.py           # Admin panel
│       └── urls.py
└── frontend/
    ├── index.html             # Main page
    ├── app.js                 # Alpine.js logic
    ├── translations.js        # Language translations (PL/EN)
    ├── styles.css             # Styling
    └── nginx.conf             # Nginx configuration
```

## Security

### Custom Admin URL

For production deployments, it's recommended to change the default `/admin/` URL to something less predictable:

```bash
# In .env file
DJANGO_ADMIN_URL=my-secret-panel-xyz123
```

This helps protect against automated attacks targeting the default Django admin path.

**Examples of custom admin URLs:**
- `/my-secret-panel/`
- `/dashboard-2024/`
- `/control-xyz/`

**Note**: The nginx configuration automatically proxies any URL containing "admin" or "panel" to the Django backend, so your custom URL will work as long as it contains one of these keywords.

## API

### GET /api/next-event/

Returns the next upcoming event from all active calendars.

**Success response (200):**
```json
{
  "success": true,
  "event": {
    "title": "Warsaw Westies Social",
    "description": "Weekly dance social...",
    "location": "Studio XYZ, Warsaw",
    "start": "2025-10-25T19:00:00+02:00",
    "end": "2025-10-25T23:00:00+02:00",
    "calendar_id": "yourcalendar@gmail.com"
  }
}
```

**Error response (404):**
```json
{
  "error": "No upcoming events",
  "message": "No upcoming events found in calendars"
}
```

**Note:** Event times are returned in ISO 8601 format with UTC offset (e.g., `2025-10-25T19:00:00+02:00`). The frontend automatically displays these times in the user's local timezone.

## Internationalization (i18n)

The application supports multiple languages with automatic detection:

- **Supported languages**: Polish (PL) and English (EN)
- **Auto-detection**: Automatically detects browser language on first visit
- **Language switcher**:
  - Desktop: top-right corner of the page
  - Mobile: inside event card, above event title
- **Persistence**: User's language preference is saved in localStorage
- **Timezone**: All times are displayed in user's local timezone

To add more languages, edit `frontend/translations.js` and add new language objects.

## How to Get Calendar ID?

1. Open Google Calendar in your browser
2. Click on the calendar you want to add
3. Go to calendar settings
4. Find "Calendar ID" in the "Integrate calendar" section
5. Copy the ID (format: name@gmail.com or a long string)

For public calendars, you can also extract it from the embed URL:
- URL: `https://calendar.google.com/calendar/embed?src=yourcalendar%40gmail.com`
- Calendar ID: `yourcalendar@gmail.com`

## Management

### Check logs

```bash
# All services
docker-compose logs -f

# Backend only
docker-compose logs -f backend

# Frontend only
docker-compose logs -f frontend
```

### Restart application

```bash
docker-compose restart
```

### Stop application

```bash
docker-compose down
```

### Update code

```bash
docker-compose down
git pull
docker-compose up -d --build
```

## Configuration

### Environment variables (docker-compose.yml)

Backend:
- `DJANGO_SECRET_KEY`: Django security key (change in production!)
- `DEBUG`: Debug mode (False in production)

### Production

Before deploying to production:

1. Change `DJANGO_SECRET_KEY` to a random, strong key
2. Set `DEBUG=False`
3. Configure `ALLOWED_HOSTS` in `westnfound/settings.py`
4. Add proper CORS settings if needed
5. Consider using an external database (PostgreSQL)
6. Configure SSL/HTTPS

## Development

### Adding new calendars

Calendars can be added in two ways:

1. **Through admin panel** (recommended):
   - http://localhost:8000/admin/events/calendar/

2. **Through Django shell**:
```bash
docker exec -it westnfound_backend python manage.py shell
```
```python
from events.models import Calendar
Calendar.objects.create(
    name="New Calendar",
    calendar_id="new@gmail.com",
    is_active=True
)
```

### Local development without Docker

Backend:
```bash
cd backend
pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Frontend - just open `frontend/index.html` in your browser or use a simple HTTP server:
```bash
cd frontend
python -m http.server 3000
```

## Troubleshooting

### No events in calendar

- Check if the Calendar ID is correct
- Make sure the calendar is public
- Check if the calendar has upcoming events
- Check logs: `docker-compose logs backend`

### CORS error

If frontend and backend are on different domains, configure CORS in `westnfound/settings.py`:
```python
CORS_ALLOWED_ORIGINS = [
    "https://your-domain.com",
]
```

### Port already in use

If ports 80 or 8000 are already in use, change them in `docker-compose.yml`:
```yaml
ports:
  - "8080:8000"  # Backend on port 8080
  - "3000:80"    # Frontend on port 3000
```

## License

MIT

## Contact

Questions? Open an issue on GitHub!
