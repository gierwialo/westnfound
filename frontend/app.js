function eventApp() {
    return {
        event: null,
        loading: true,
        error: false,
        errorMessage: '',
        lastUpdate: '',
        countdownInterval: null,

        init() {
            this.loadEvent();
            // Auto-refresh every 5 minutes
            setInterval(() => this.loadEvent(), 5 * 60 * 1000);
        },

        async loadEvent() {
            this.loading = true;
            this.error = false;

            try {
                const response = await fetch('/api/next-event/');
                const data = await response.json();

                if (!response.ok) {
                    throw new Error(data.message || 'Błąd pobierania wydarzenia');
                }

                this.event = data.event;
                this.lastUpdate = new Date().toLocaleTimeString('pl-PL');
                this.startCountdown();
            } catch (err) {
                this.error = true;
                this.errorMessage = err.message;
                console.error('Error loading event:', err);
            } finally {
                this.loading = false;
            }
        },

        formatDate(dateString) {
            if (!dateString) return '';

            const date = new Date(dateString);
            const options = {
                weekday: 'long',
                year: 'numeric',
                month: 'long',
                day: 'numeric',
                hour: '2-digit',
                minute: '2-digit'
            };

            return date.toLocaleDateString('pl-PL', options);
        },

        formatDescription(description) {
            if (!description) return '';

            // Convert URLs to links
            const urlRegex = /(https?:\/\/[^\s]+)/g;
            let formatted = description.replace(urlRegex, '<a href="$1" target="_blank" rel="noopener">$1</a>');

            // Convert newlines to <br>
            formatted = formatted.replace(/\n/g, '<br>');

            return formatted;
        },

        getTimeUntil(dateString) {
            if (!dateString) return '';

            const now = new Date();
            const eventDate = new Date(dateString);
            const diff = eventDate - now;

            if (diff < 0) return 'Wydarzenie się już odbyło';

            const days = Math.floor(diff / (1000 * 60 * 60 * 24));
            const hours = Math.floor((diff % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60));
            const minutes = Math.floor((diff % (1000 * 60 * 60)) / (1000 * 60));

            let result = [];
            if (days > 0) result.push(`${days} dni`);
            if (hours > 0) result.push(`${hours} godz.`);
            if (minutes > 0 || result.length === 0) result.push(`${minutes} min.`);

            return result.join(', ');
        },

        startCountdown() {
            // Clear existing interval
            if (this.countdownInterval) {
                clearInterval(this.countdownInterval);
            }

            // Update countdown every minute
            this.countdownInterval = setInterval(() => {
                this.$nextTick();
            }, 60000);
        },

        addToCalendar() {
            if (!this.event) return;

            const startDate = new Date(this.event.start);
            const endDate = new Date(this.event.end);

            // Format dates for Google Calendar (YYYYMMDDTHHmmssZ)
            const formatGoogleDate = (date) => {
                return date.toISOString().replace(/[-:]/g, '').split('.')[0] + 'Z';
            };

            // Build Google Calendar URL
            const params = new URLSearchParams({
                action: 'TEMPLATE',
                text: this.event.title,
                dates: `${formatGoogleDate(startDate)}/${formatGoogleDate(endDate)}`,
                details: this.event.description || '',
                location: this.event.location || '',
            });

            const url = `https://calendar.google.com/calendar/render?${params.toString()}`;
            window.open(url, '_blank');
        },

        openNavigation() {
            if (!this.event?.location) return;

            // Google Maps URL with navigation
            const url = `https://www.google.com/maps/dir/?api=1&destination=${encodeURIComponent(this.event.location)}`;
            window.open(url, '_blank');
        }
    };
}
