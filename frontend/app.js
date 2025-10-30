function eventApp() {
    return {
        events: [],
        currentEventIndex: 0,
        loading: true,
        error: false,
        errorMessage: '',
        lastUpdate: '',
        countdownInterval: null,
        currentLang: 'pl',
        touchStartX: 0,
        touchEndX: 0,

        get event() {
            return this.events[this.currentEventIndex] || null;
        },

        init() {
            this.initLanguage();
            this.loadEvent();
            this.initSwipeHandlers();
            // Auto-refresh every 5 minutes
            setInterval(() => this.loadEvent(), 5 * 60 * 1000);
        },

        initSwipeHandlers() {
            const container = document.querySelector('.event-card');
            if (!container) return;

            container.addEventListener('touchstart', (e) => {
                this.touchStartX = e.changedTouches[0].screenX;
            });

            container.addEventListener('touchend', (e) => {
                this.touchEndX = e.changedTouches[0].screenX;
                this.handleSwipe();
            });
        },

        handleSwipe() {
            const swipeThreshold = 50;
            const diff = this.touchStartX - this.touchEndX;

            if (Math.abs(diff) > swipeThreshold) {
                if (diff > 0) {
                    // Swipe left - next event
                    this.nextEvent();
                } else {
                    // Swipe right - previous event
                    this.previousEvent();
                }
            }
        },

        nextEvent() {
            if (this.currentEventIndex < this.events.length - 1) {
                this.currentEventIndex++;
                this.startCountdown();
            }
        },

        previousEvent() {
            if (this.currentEventIndex > 0) {
                this.currentEventIndex--;
                this.startCountdown();
            }
        },

        hasNextEvent() {
            return this.currentEventIndex < this.events.length - 1;
        },

        hasPreviousEvent() {
            return this.currentEventIndex > 0;
        },

        initLanguage() {
            // Check localStorage first
            const savedLang = localStorage.getItem('preferredLanguage');
            if (savedLang && translations[savedLang]) {
                this.currentLang = savedLang;
            } else {
                // Auto-detect browser language
                const browserLang = navigator.language.split('-')[0]; // 'pl-PL' -> 'pl'
                this.currentLang = translations[browserLang] ? browserLang : 'pl';
            }
            this.updateHtmlLang();
        },

        setLanguage(lang) {
            if (translations[lang]) {
                this.currentLang = lang;
                localStorage.setItem('preferredLanguage', lang);
                this.updateHtmlLang();
            }
        },

        updateHtmlLang() {
            document.documentElement.lang = this.currentLang;
        },

        t(key) {
            return translations[this.currentLang]?.[key] || key;
        },

        async loadEvent() {
            this.loading = true;
            this.error = false;

            try {
                const response = await fetch('/api/next-events/?limit=3');
                const data = await response.json();

                if (!response.ok) {
                    throw new Error(data.message || this.t('errorDefault'));
                }

                this.events = data.events || [];
                this.currentEventIndex = 0;
                this.lastUpdate = new Date().toLocaleTimeString(this.currentLang + '-' + this.currentLang.toUpperCase());
                this.startCountdown();

                // Re-initialize swipe handlers after DOM update
                this.$nextTick(() => this.initSwipeHandlers());
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

            const locale = this.currentLang + '-' + this.currentLang.toUpperCase();
            return date.toLocaleDateString(locale, options);
        },

        formatDescription(description) {
            if (!description) return '';

            // If description already contains HTML tags, return as-is
            if (/<[a-z][\s\S]*>/i.test(description)) {
                return description.replace(/\n/g, '<br>');
            }

            // Convert URLs to links (only for plain text)
            const urlRegex = /(https?:\/\/[^\s]+)/g;
            let formatted = description.replace(urlRegex, '<a href="$1" target="_blank" rel="noopener">$1</a>');

            // Convert newlines to <br>
            formatted = formatted.replace(/\n/g, '<br>');

            return formatted;
        },

        isEventOngoing() {
            if (!this.event) return false;
            const now = new Date();
            const startDate = new Date(this.event.start);
            const endDate = new Date(this.event.end);
            return now >= startDate && now < endDate;
        },

        getTimeUntil() {
            if (!this.event) return '';

            const now = new Date();
            const startDate = new Date(this.event.start);
            const endDate = new Date(this.event.end);

            // Event is currently happening
            if (now >= startDate && now < endDate) {
                return this.t('eventOngoing');
            }

            // Event hasn't started yet - show countdown to start
            if (now < startDate) {
                const diff = startDate - now;
                const days = Math.floor(diff / (1000 * 60 * 60 * 24));
                const hours = Math.floor((diff % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60));
                const minutes = Math.floor((diff % (1000 * 60 * 60)) / (1000 * 60));

                let result = [];
                if (days > 0) result.push(`${days} ${this.t('days')}`);
                if (hours > 0) result.push(`${hours} ${this.t('hours')}`);
                if (minutes > 0 || result.length === 0) result.push(`${minutes} ${this.t('minutes')}`);

                return result.join(', ');
            }

            // Event has ended
            return this.t('eventEnded');
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
