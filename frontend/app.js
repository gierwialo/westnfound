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
        swipeHandlersInitialized: false,
        unknownCity: false,
        cities: [],
        refreshTimer: null,
        inFlight: false,
        // Reading `now` is what ties the countdown to the clock; see startCountdown()
        now: Date.now(),

        REFRESH_MS: 5 * 60 * 1000,
        // A refresh usually fails because the network has just gone away with
        // the phone screen. It comes back in seconds, so retry in seconds.
        RETRY_MS: 20 * 1000,
        FETCH_TIMEOUT_MS: 15 * 1000,

        get event() {
            return this.events[this.currentEventIndex] || null;
        },

        get currentCity() {
            return this.cities.find(city => city.is_current) || null;
        },

        get namedCity() {
            // Saying "Warszawa" when Warsaw is the only city we have adds
            // nothing; the name earns its place once there is a choice.
            return this.cities.length > 1 ? this.currentCity : null;
        },

        init() {
            this.initLanguage();
            this.setCanonical('/');
            this.updateDescription();
            this.loadCities();
            // Every load schedules the next one, so there is one timer, and a
            // failed refresh can come back sooner than a successful one.
            this.loadEvent();

            // A phone whose screen was locked, or a laptop back from sleep,
            // returns with a timer that has not run for a while and possibly a
            // refresh that died with the old network. Catch up on the way back
            // in instead of waiting out the rest of the interval.
            document.addEventListener('visibilitychange', () => {
                if (!document.hidden) this.loadEvent({ background: true });
            });
            window.addEventListener('online', () => this.loadEvent({ background: true }));
        },

        scheduleRefresh(delay) {
            if (this.refreshTimer) clearTimeout(this.refreshTimer);
            this.refreshTimer = setTimeout(
                () => this.loadEvent({ background: true }),
                delay
            );
        },

        initSwipeHandlers() {
            // Only initialize once to prevent duplicate event listeners
            if (this.swipeHandlersInitialized) return;

            const container = document.querySelector('.event-card');
            if (!container) return;

            container.addEventListener('touchstart', (e) => {
                this.touchStartX = e.changedTouches[0].screenX;
            });

            container.addEventListener('touchend', (e) => {
                this.touchEndX = e.changedTouches[0].screenX;
                this.handleSwipe();
            });

            this.swipeHandlersInitialized = true;
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
                this.updateTitle();
            }
        },

        updateHtmlLang() {
            document.documentElement.lang = this.currentLang;
        },

        updateTitle() {
            const city = this.namedCity;
            document.title = city
                ? `${this.t('title')} - ${city.name}`
                : this.t('title');
            this.updateDescription();
        },

        updateDescription() {
            const city = this.namedCity;
            this.setMeta('description', city
                ? this.t('metaDescriptionCity').replace('{city}', city.name)
                : this.t('metaDescription'));
        },

        // Description and canonical address are for crawlers, not for the
        // page. Both have to be set here rather than in the HTML: the file is
        // one static document served for every city, so a fixed canonical
        // would point Łódź and Kraków at the apex and ask Google to drop them.
        setMeta(name, content) {
            let tag = document.head.querySelector(`meta[name="${name}"]`);
            if (!tag) {
                tag = document.createElement('meta');
                tag.setAttribute('name', name);
                document.head.appendChild(tag);
            }
            tag.setAttribute('content', content);
        },

        // One address per page. /calendar and /kalendarz are the same page in
        // two spellings, and www is the same site as the apex - left alone,
        // a crawler treats them as duplicates and picks a winner itself.
        setCanonical(path) {
            let tag = document.head.querySelector('link[rel="canonical"]');
            if (!tag) {
                tag = document.createElement('link');
                tag.setAttribute('rel', 'canonical');
                document.head.appendChild(tag);
            }
            const host = location.host.replace(/^www\./, '');
            tag.setAttribute('href', `${location.protocol}//${host}${path}`);
        },

        t(key) {
            return translations[this.currentLang]?.[key] || key;
        },

        async loadCities() {
            try {
                const response = await fetch('/api/cities/');
                const data = await response.json();
                this.cities = data.cities || [];
                this.updateTitle();
            } catch (err) {
                // The footer and the unknown-city page degrade to nothing;
                // never let this break the event card.
                console.error('Error loading cities:', err);
            }
        },

        async fetchJson(url) {
            // fetch() on its own waits forever. A request that left just as the
            // network went away never settles, and without a deadline the page
            // sits on a spinner until the visitor gives up and reloads.
            const controller = new AbortController();
            const timer = setTimeout(() => controller.abort(), this.FETCH_TIMEOUT_MS);
            try {
                const response = await fetch(url, { signal: controller.signal });
                return { response, data: await response.json() };
            } finally {
                clearTimeout(timer);
            }
        },

        async loadEvent({ background = false } = {}) {
            if (this.inFlight) return;
            this.inFlight = true;

            // A background refresh runs behind a card someone may be reading.
            // It may replace the data; it may never take the page away. So no
            // spinner, and a failure leaves the last good events on screen -
            // stale by minutes beats gone. Only the first load, the retry
            // button and a refresh over an error own the whole page.
            const silent = background
                && this.events.length > 0
                && !this.error
                && !this.unknownCity;

            if (!silent) {
                this.loading = true;
                this.error = false;
                this.unknownCity = false;
            }

            let succeeded = false;
            try {
                const { response, data } = await this.fetchJson('/api/next-events/?limit=3');

                if (data.error === 'Unknown city') {
                    // The address names a city we do not serve. Not an error
                    // the visitor can retry out of, so it gets its own state.
                    if (!silent) this.unknownCity = true;
                    succeeded = true;
                    return;
                }

                if (!response.ok) {
                    throw new Error(data.message || this.t('errorDefault'));
                }

                this.events = data.events || [];
                this.currentEventIndex = 0;
                this.lastUpdate = new Date().toLocaleTimeString(this.currentLang + '-' + this.currentLang.toUpperCase());
                this.error = false;
                this.startCountdown();
                succeeded = true;

                // Re-initialize swipe handlers after DOM update
                this.$nextTick(() => this.initSwipeHandlers());
            } catch (err) {
                console.error('Error loading event:', err);
                if (!silent) {
                    this.error = true;
                    this.errorMessage = err.message;
                }
            } finally {
                this.inFlight = false;
                if (!silent) this.loading = false;
                this.scheduleRefresh(succeeded ? this.REFRESH_MS : this.RETRY_MS);
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
            const now = new Date(this.now);
            const startDate = new Date(this.event.start);
            const endDate = new Date(this.event.end);
            return now >= startDate && now < endDate;
        },

        getTimeUntil() {
            if (!this.event) return '';

            const now = new Date(this.now);
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

            // Alpine re-runs an expression when a property it read changes, so
            // moving `now` is what moves the countdown. The previous timer
            // called $nextTick(), which returns a promise and changes no state,
            // so the numbers only ever moved when a refresh replaced the
            // events - and stood still whenever refreshes failed.
            this.now = Date.now();
            this.countdownInterval = setInterval(() => {
                this.now = Date.now();
            }, 30000);
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
