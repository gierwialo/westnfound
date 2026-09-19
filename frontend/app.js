function eventApp() {
    return {
        events: [],
        currentEventIndex: 0,
        loading: true,
        error: false,
        currentLang: 'pl',
        unknownCity: false,
        cities: [],
        refreshTimer: null,
        inFlight: false,
        // Reading `now` is what ties the day badge to the clock; see init()
        now: Date.now(),
        // The open sheet: null, 'details' or 'city'. `detail` is the event the
        // details sheet shows, kept as its own object so a background refresh
        // cannot change it under the reader.
        sheet: null,
        detail: null,
        returnFocus: null,
        shared: false,

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

        get showEvents() {
            return !this.loading && !this.error && !this.unknownCity && this.events.length > 0;
        },

        get showEmpty() {
            return !this.loading && !this.error && !this.unknownCity && this.events.length === 0;
        },

        init() {
            this.initLanguage();
            this.updateDescription();
            this.loadCities();
            // Every load schedules the next one, so there is one timer, and a
            // failed refresh can come back sooner than a successful one.
            this.loadEvent();
            // The badge says "today" or "tomorrow"; let it follow the clock.
            setInterval(() => { this.now = Date.now(); }, 60 * 1000);

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

        // The description is for crawlers, not for the page. Django writes
        // one per city before the document leaves the server; this rewrites
        // it once the reader's language is known, which only the browser can
        // tell us - it lives in localStorage and arrives with no request.
        // The canonical address is set server-side only, so a crawler sees it
        // whether or not it runs any of this.
        setMeta(name, content) {
            let tag = document.head.querySelector(`meta[name="${name}"]`);
            if (!tag) {
                tag = document.createElement('meta');
                tag.setAttribute('name', name);
                document.head.appendChild(tag);
            }
            tag.setAttribute('content', content);
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
                this.error = false;
                this.now = Date.now();
                succeeded = true;
            } catch (err) {
                console.error('Error loading event:', err);
                if (!silent) {
                    this.error = true;
                }
            } finally {
                this.inFlight = false;
                if (!silent) this.loading = false;
                this.scheduleRefresh(succeeded ? this.REFRESH_MS : this.RETRY_MS);
            }
        },

        // The day badge on an event, from the same rules as the app.
        get badge() {
            return this.badgeFor(this.event);
        },

        badgeFor(event) {
            if (!event) return '';
            const label = GnwModel.relativeDayLabel(event, new Date(this.now));
            switch (label.kind) {
                case 'now': return this.t('badgeNow');
                case 'today': return this.t('badgeToday');
                case 'tomorrow': return this.t('badgeTomorrow');
                default: {
                    // 7 January 2024 was a Sunday, so day 0 of getDay() is that date.
                    const name = new Date(2024, 0, 7 + label.weekday)
                        .toLocaleDateString(this.locale, { weekday: 'long' });
                    return this.t('badgeInDays')
                        .replace('{weekday}', name.charAt(0).toUpperCase() + name.slice(1))
                        .replace('{n}', label.days);
                }
            }
        },

        // "sobota, 19 września" and "20:00 – 00:00": the two lines of the date row.
        dayLine(dateString) {
            return new Date(dateString)
                .toLocaleDateString(this.locale, { weekday: 'long', day: 'numeric', month: 'long' });
        },

        timeRange(event) {
            if (!event) return '';
            const start = this.timeOfDay(event.start);
            return event.end ? start + ' – ' + this.timeOfDay(event.end) : start;
        },

        // Venue on the first line, street and city on the second.
        get where() {
            return this.whereOf(this.event);
        },

        whereOf(event) {
            const cityName = this.currentCity ? this.currentCity.name : '';
            return GnwModel.splitLocation(event ? event.location : '', cityName);
        },

        placeOf(location) {
            return GnwModel.splitLocation(location, '').place;
        },

        get locale() {
            return this.currentLang + '-' + this.currentLang.toUpperCase();
        },

        // The pieces of a "Potem" row: weekday and day of the month for the
        // tile, and the start time for the second line.
        shortWeekday(dateString) {
            const date = new Date(dateString);
            // The usual two-letter Polish abbreviations, Sunday first, as in
            // the app: Intl spells them 2 to 6 letters, too wide for the tile.
            if (this.currentLang === 'pl') return ['nd', 'pn', 'wt', 'śr', 'cz', 'pt', 'so'][date.getDay()];
            return date.toLocaleDateString(this.locale, { weekday: 'short' });
        },

        dayOfMonth(dateString) {
            return new Date(dateString).getDate();
        },

        timeOfDay(dateString) {
            return new Date(dateString).toLocaleTimeString(this.locale, { hour: '2-digit', minute: '2-digit' });
        },

        addToCalendar(event) {
            if (!event) return;

            const startDate = new Date(event.start);
            const endDate = new Date(event.end);

            // Format dates for Google Calendar (YYYYMMDDTHHmmssZ)
            const formatGoogleDate = (date) => {
                return date.toISOString().replace(/[-:]/g, '').split('.')[0] + 'Z';
            };

            // Build Google Calendar URL
            const params = new URLSearchParams({
                action: 'TEMPLATE',
                text: event.title,
                dates: `${formatGoogleDate(startDate)}/${formatGoogleDate(endDate)}`,
                details: event.description || '',
                location: event.location || '',
            });

            const url = `https://calendar.google.com/calendar/render?${params.toString()}`;
            window.open(url, '_blank');
        },

        openNavigation(event) {
            if (!event?.location) return;

            // Google Maps URL with navigation
            const url = `https://www.google.com/maps/dir/?api=1&destination=${encodeURIComponent(event.location)}`;
            window.open(url, '_blank');
        },

        // --- Sheets --------------------------------------------------------

        openDetails(event, domEvent) {
            this.detail = event;
            this.openSheet('details', domEvent);
        },

        openSheet(name, domEvent) {
            this.returnFocus = (domEvent && domEvent.currentTarget) || document.activeElement;
            this.sheet = name;
            // The page behind must not scroll under a sheet.
            document.documentElement.classList.add('sheet-open');
            // Focus the dialog itself: it is announced by its name, and the
            // first Tab goes to its first control.
            this.$nextTick(() => this.$refs.sheetBox?.focus());
        },

        closeSheet() {
            if (!this.sheet) return;
            this.sheet = null;
            this.detail = null;
            document.documentElement.classList.remove('sheet-open');
            const back = this.returnFocus;
            this.returnFocus = null;
            // A refresh may have replaced the element that opened the sheet.
            if (back && back.isConnected) back.focus();
        },

        // Tab stays inside the open sheet.
        trapFocus(domEvent) {
            const box = this.$refs.sheetBox;
            if (!this.sheet || !box) return;
            const items = [...box.querySelectorAll('a[href], button:not([disabled])')]
                .filter(el => el.offsetParent !== null);
            if (items.length === 0) return;
            const first = items[0];
            const last = items[items.length - 1];
            const active = document.activeElement;
            if (domEvent.shiftKey && (active === first || active === box || !box.contains(active))) {
                domEvent.preventDefault();
                last.focus();
            } else if (!domEvent.shiftKey && (active === last || !box.contains(active))) {
                domEvent.preventDefault();
                first.focus();
            }
        },

        // The description as the sheet shows it: the Facebook link pulled out
        // into a row, the rest as text with its http(s) links marked.
        get description() {
            const event = this.detail;
            if (!event) return { text: '', parts: [], facebook: null };
            const facebook = GnwModel.extractFacebookLink(event.description);
            const text = facebook ? facebook.textWithoutLink : GnwModel.stripHtml(event.description);
            return { text, parts: GnwModel.linkify(text), facebook };
        },

        // An event with no end is shown by its date alone, not as 20:00-Invalid.
        forModel(event) {
            return event.end ? event : Object.assign({}, event, { allDay: true });
        },

        correctionHref(event) {
            if (!event) return '#';
            const city = this.currentCity ? this.currentCity.name : '';
            const mail = GnwModel.correctionMail(
                this.forModel(event), city, this.currentLang, translations[this.currentLang].correction);
            return GnwModel.mailtoHref(mail);
        },

        // The system share sheet where the browser has one; otherwise the
        // message goes to the clipboard, and the icon says so for two seconds.
        async share(event) {
            if (!event || !this.currentCity) return;
            const text = GnwModel.shareMessage(
                this.forModel(event), this.currentCity.slug, this.currentLang, translations[this.currentLang]);
            try {
                if (navigator.share) {
                    await navigator.share({ text });
                    return;
                }
                await navigator.clipboard.writeText(text);
                this.shared = true;
                setTimeout(() => { this.shared = false; }, 2000);
            } catch (err) {
                // Closing the share sheet rejects with AbortError; not a failure.
                if (err && err.name !== 'AbortError') console.error('Error sharing:', err);
            }
        }
    };
}
