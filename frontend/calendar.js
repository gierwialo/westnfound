function calendarPage() {
    return {
        loading: true,
        error: false,
        unknownCity: false,
        currentLang: 'pl',
        city: null,
        cities: [],
        calendarId: '',
        timezone: 'Europe/Warsaw',
        googleUrl: '',
        copied: false,
        // A month grid on a phone is a wall of coloured slivers; the agenda
        // view is the same calendar, readable. Which one applies is decided
        // once and only revisited when the window crosses the threshold, so
        // dragging a window edge does not reload the calendar on every pixel.
        NARROW_PX: 700,
        isNarrow: false,
        FETCH_TIMEOUT_MS: 15 * 1000,

        // Podawany przez /api/calendar/, bo tylko serwer wie, pod jakim adresem
        // mieszka to miasto. Skladany tu wczesniej z location.origin wiazal
        // kazdego, kto subskrybowal z apeksu, z gdzienawesta.com zamiast
        // z Warszawa - a subskrypcje ustawia sie raz i nikt do niej nie wraca.
        // Awaryjnie zostaje stary sposob: lepiej podac adres z tego hosta niz
        // pusty, gdy zapytanie do API nie doszlo.
        feedUrlFromApi: '',

        get feedUrl() {
            return this.feedUrlFromApi
                || `${location.origin}/${this.t('calendarPath')}.ics`;
        },

        get webcalUrl() {
            // webcal:// is what makes a calendar app offer to subscribe
            // instead of a browser offering to download. Nothing serves it -
            // the app rewrites it back to https before asking us.
            return this.feedUrl.replace(/^https?:/, 'webcal:');
        },

        get embedSrc() {
            if (!this.calendarId) return '';
            const params = new URLSearchParams({
                src: this.calendarId,
                ctz: this.timezone,
                mode: this.isNarrow ? 'AGENDA' : 'MONTH',
                // We already say whose calendar this is, in our own words.
                showTitle: '0',
                showPrint: '0',
                showTz: '0',
                showCalendars: '0',
                wkst: '2',              // weeks start on Monday in Poland
                hl: this.currentLang,
            });
            return `https://calendar.google.com/calendar/embed?${params.toString()}`;
        },

        init() {
            this.initLanguage();
            // of the four the visitor arrived through.
            this.updateDescription();
            this.isNarrow = window.innerWidth < this.NARROW_PX;
            this.load();
            this.loadCities();

            window.addEventListener('resize', () => {
                const narrow = window.innerWidth < this.NARROW_PX;
                if (narrow !== this.isNarrow) this.isNarrow = narrow;
            });
        },

        initLanguage() {
            const savedLang = localStorage.getItem('preferredLanguage');
            if (savedLang && translations[savedLang]) {
                this.currentLang = savedLang;
            } else {
                const browserLang = navigator.language.split('-')[0];
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
            document.title = this.city
                ? `${this.t('title')} - ${this.t('calendarTitle')} - ${this.city.name}`
                : `${this.t('title')} - ${this.t('calendarTitle')}`;
            this.updateDescription();
        },

        updateDescription() {
            this.setMeta('description', this.city
                ? this.t('metaDescriptionCalendarCity').replace('{city}', this.city.name)
                : this.t('metaDescriptionCalendar'));
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

        async load() {
            this.loading = true;
            this.error = false;
            this.unknownCity = false;

            // fetch() on its own waits forever; a request that left as the
            // network went away would leave this page on its spinner.
            const controller = new AbortController();
            const timer = setTimeout(() => controller.abort(), this.FETCH_TIMEOUT_MS);
            try {
                const response = await fetch('/api/calendar/', { signal: controller.signal });
                const data = await response.json();

                if (response.status === 404) {
                    this.unknownCity = true;
                    return;
                }
                if (!response.ok || !data.success) {
                    this.error = true;
                    return;
                }

                this.city = data.city;
                this.feedUrlFromApi = data.feed_url || '';
                this.calendarId = data.calendar_id;
                this.timezone = data.timezone;
                this.googleUrl = data.google_url;
                this.updateTitle();
            } catch (err) {
                console.error('Error loading calendar:', err);
                this.error = true;
            } finally {
                clearTimeout(timer);
                this.loading = false;
            }
        },

        async loadCities() {
            // Only the unknown-city card uses these, and it is the one case
            // where the request above has already failed - so this one stands
            // on its own and stays silent when it cannot deliver.
            try {
                const response = await fetch('/api/cities/');
                const data = await response.json();
                this.cities = data.cities || [];
            } catch (err) {
                console.error('Error loading cities:', err);
            }
        },

        async copyFeedUrl() {
            try {
                await navigator.clipboard.writeText(this.feedUrl);
                this.copied = true;
                setTimeout(() => { this.copied = false; }, 2000);
            } catch (err) {
                // Clipboard access can be refused outright (no permission, or
                // an insecure origin). The address is printed under the
                // buttons precisely so there is always a way to get it.
                console.error('Error copying the feed address:', err);
            }
        },
    };
}
