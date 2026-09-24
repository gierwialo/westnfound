// The map of cities on gdzienawesta.com: the list with what is on next in each
// city, the map that draws the same list, and the shortcut back to the city
// last visited. The arithmetic - projection, labels, date tile - is in
// cities.js; this is the page around it.
function hubApp() {
    return {
        currentLang: 'pl',
        // From the list Django wrote into the page, not from a request: the
        // names are there before any script runs, and reading them back costs
        // nothing. { slug, name, url, pos } with pos null for a city with no
        // coordinates - listed, but not on the map.
        cities: [],
        // What /api/cities/next/ said, by slug: an event, or null for a city
        // with nothing planned. `nextState` is 'loading', 'ready' or 'failed';
        // a failed request leaves the list with its names and nothing else.
        next: {},
        nextState: 'loading',
        mineSlug: null,
        // The slug under the pointer, on the map or on the list, so the other
        // one lights up with it.
        hl: null,
        now: Date.now(),

        REFRESH_MS: 5 * 60 * 1000,
        FETCH_TIMEOUT_MS: 15 * 1000,

        outline: GnwCities.OUTLINE,

        init() {
            this.cities = [...document.querySelectorAll('[data-server-list] a[data-slug]')].map(link => ({
                slug: link.dataset.slug,
                name: link.dataset.name,
                url: link.getAttribute('href'),
                pos: GnwCities.projectPercent(
                    link.dataset.lat ? Number(link.dataset.lat) : null,
                    link.dataset.lon ? Number(link.dataset.lon) : null),
            }));
            this.mineSlug = GnwModel.cityFromCookies(document.cookie);

            this.initLanguage();
            this.loadNext();
            setInterval(() => this.loadNext(), this.REFRESH_MS);
            // The tile says "today" or a weekday; let it follow the clock.
            setInterval(() => { this.now = Date.now(); }, 60 * 1000);

            // Labels are measured, so they wait for the fonts, and are laid
            // out again whenever the map changes width.
            this.$nextTick(() => {
                const map = this.$refs.map;
                if (!map) return;
                const layout = () => requestAnimationFrame(() => this.layoutLabels());
                (document.fonts ? document.fonts.ready : Promise.resolve()).then(layout);
                if (window.ResizeObserver) new ResizeObserver(layout).observe(map);
            });
        },

        get mapped() {
            return this.cities.filter(city => city.pos);
        },

        get mine() {
            return this.cities.find(city => city.slug === this.mineSlug) || null;
        },

        // --- Language, title, description ----------------------------------

        initLanguage() {
            const saved = localStorage.getItem('preferredLanguage');
            if (saved && translations[saved]) {
                this.currentLang = saved;
            } else {
                const browserLang = navigator.language.split('-')[0];
                this.currentLang = translations[browserLang] ? browserLang : 'pl';
            }
            this.applyLanguage();
        },

        setLanguage(lang) {
            if (!translations[lang]) return;
            this.currentLang = lang;
            localStorage.setItem('preferredLanguage', lang);
            this.applyLanguage();
        },

        applyLanguage() {
            document.documentElement.lang = this.currentLang;
            document.title = this.t('title');
            // Django wrote the Polish one; this follows the reader's language.
            const description = this.cities.length > 1
                ? this.t('metaDescriptionHub').replace('{count}', this.cities.length)
                : this.t('metaDescription');
            document.head.querySelector('meta[name="description"]')?.setAttribute('content', description);
        },

        t(key) {
            return translations[this.currentLang]?.[key] || key;
        },

        get lead() {
            return this.t('hubLead').replace('{count}', this.cities.length);
        },

        get locale() {
            return this.currentLang + '-' + this.currentLang.toUpperCase();
        },

        // --- What is on next in each city ------------------------------------

        async loadNext() {
            const controller = new AbortController();
            const timer = setTimeout(() => controller.abort(), this.FETCH_TIMEOUT_MS);
            try {
                const response = await fetch('/api/cities/next/', { signal: controller.signal });
                if (!response.ok) throw new Error(`HTTP ${response.status}`);
                const data = await response.json();
                const next = {};
                for (const city of data.cities || []) next[city.slug] = city.event;
                this.next = next;
                this.nextState = 'ready';
                this.now = Date.now();
            } catch (err) {
                console.error('Error loading the next events:', err);
                // A refresh that fails keeps what the last one brought.
                if (this.nextState !== 'ready') this.nextState = 'failed';
            } finally {
                clearTimeout(timer);
            }
        },

        // The tile and the second line of a row, or of the shortcut.
        // { tile: null } while there is nothing to show beyond the name.
        rowFor(slug) {
            if (this.nextState !== 'ready' || !(slug in this.next)) return { tile: null, line: '' };
            const event = this.next[slug];
            if (!event) {
                return { tile: { kind: 'none', top: ' ', day: '–' }, line: this.t('emptyTitle') };
            }
            const tile = GnwCities.dateTile(event.start, new Date(this.now));
            const top = tile.kind === 'today' ? this.t('hubToday')
                : tile.kind === 'weekday' ? this.t('hubWeekdays')[tile.index]
                : this.t('hubMonths')[tile.index];
            // The time first: a long title would otherwise push it out of sight.
            const time = new Date(event.start)
                .toLocaleTimeString(this.locale, { hour: '2-digit', minute: '2-digit' });
            return { tile: { kind: tile.kind, top, day: tile.day }, line: `${time} · ${event.title}` };
        },

        // --- The map -----------------------------------------------------------

        layoutLabels() {
            const map = this.$refs.map;
            if (!map || !map.offsetWidth) return;
            // The narrowest phones get labels a pixel smaller; set before
            // measuring, since it changes what there is to measure.
            map.classList.toggle('narrow', map.offsetWidth < 320);
            const width = map.offsetWidth;
            const height = map.offsetHeight;
            const pins = [...map.querySelectorAll('.pin')];
            const items = pins.map(pin => {
                const label = pin.querySelector('.lab');
                return {
                    x: parseFloat(pin.style.left) / 100 * width,
                    y: parseFloat(pin.style.top) / 100 * height,
                    w: label.offsetWidth,
                    h: label.offsetHeight,
                };
            });
            // Written straight onto the pins rather than kept as state: it is
            // a fact about this width, and nothing else reads it.
            GnwCities.placeLabels(items, width, height)
                .forEach((side, i) => { pins[i].dataset.side = side; });
        },
    };
}
