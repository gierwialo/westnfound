/*
 * Pure functions behind the event cards and the details sheet: the day badge,
 * the address, the Facebook link, the description as text, and the two texts
 * that leave the page (share and "suggest a correction").
 *
 * No framework and no build step. In the browser the functions hang on
 * window.GnwModel; in Node (the tests) they are the module's exports. The
 * wording lives in translations.js and comes in as an argument.
 *
 * Tests: tests/frontend/model.test.js, run with node --test (see README).
 */
(function (root) {
    'use strict';

    // --- Day badge -----------------------------------------------------------

    function localDayNumber(date) {
        // A calendar day in the visitor's time zone, so a daylight-saving
        // change does not turn a day into 23 or 25 hours.
        return Date.UTC(date.getFullYear(), date.getMonth(), date.getDate()) / 86400000;
    }

    /**
     * What the day badge says, as data: { kind: 'now' | 'today' | 'tomorrow' }
     * or { kind: 'inDays', weekday, days } with weekday as Date#getDay().
     */
    function relativeDayLabel(event, now) {
        const start = new Date(event.start);
        if (start <= now && now < new Date(event.end)) {
            return { kind: 'now' };
        }
        const days = localDayNumber(start) - localDayNumber(now);
        if (days <= 0) {
            return { kind: 'today' };
        }
        if (days === 1) {
            return { kind: 'tomorrow' };
        }
        return { kind: 'inDays', weekday: start.getDay(), days: days };
    }

    // --- Address -------------------------------------------------------------

    const POSTCODE = /\d{2}-\d{3}/;
    const COUNTRY = /^(poland|polska)$/i;

    /**
     * "Venue, Street 1, 00-000 Town, Poland" -> the venue and the street. The
     * postcode-and-town and the country are dropped: the page already knows
     * the city.
     */
    function splitLocation(location, cityName) {
        const segments = String(location || '')
            .split(',')
            .map(function (segment) { return segment.trim(); })
            .filter(function (segment) { return segment.length > 0; });
        if (segments.length === 0) {
            return { place: '', street: '', streetWithCity: '' };
        }
        const second = segments[1];
        const noise = second !== undefined && (POSTCODE.test(second) || COUNTRY.test(second));
        const street = second !== undefined && !noise ? second : '';
        return {
            place: segments[0],
            street: street,
            streetWithCity: street ? street + ', ' + cityName : '',
        };
    }

    // --- Description ---------------------------------------------------------

    /**
     * HTML from the calendar -> plain text. The page puts the result into
     * text nodes only: whoever can edit a city's calendar must not be able to
     * put markup, let alone a script, on the page.
     */
    function stripHtml(input) {
        return String(input || '')
            .replace(/<br\s*\/?>/gi, '\n')
            .replace(/<\/(p|div|li)>/gi, '\n')
            .replace(/<[^>]+>/g, '')
            .replace(/&amp;/g, '&')
            .replace(/&lt;/g, '<')
            .replace(/&gt;/g, '>')
            .replace(/&quot;/g, '"')
            .replace(/&#39;/g, "'")
            .replace(/&nbsp;/g, ' ')
            .replace(/\n{3,}/g, '\n\n')
            .trim();
    }

    const URL_PATTERN = /https?:\/\/[^\s<>"']+/g;

    /**
     * Text -> [{ text, url }], url null for plain text. Only http(s) links
     * are ever links; trailing punctuation stays plain.
     */
    function linkify(text) {
        const segments = [];
        let cursor = 0;
        for (const match of String(text).matchAll(URL_PATTERN)) {
            let url = match[0];
            const trimmed = url.replace(/[.,;:!?)\]]+$/, '');
            url = trimmed.length > 0 ? trimmed : url;
            const start = match.index;
            if (start > cursor) {
                segments.push({ text: text.slice(cursor, start), url: null });
            }
            segments.push({ text: url, url: url });
            cursor = start + url.length;
        }
        if (cursor < text.length) {
            segments.push({ text: text.slice(cursor), url: null });
        }
        return segments;
    }

    const FACEBOOK_HOSTS = ['facebook.com', 'www.facebook.com', 'm.facebook.com', 'fb.me'];

    function hostOf(url) {
        const match = /^https?:\/\/([^/:?#]+)/i.exec(url);
        return match ? match[1].toLowerCase() : '';
    }

    /**
     * The first Facebook link in the description, and the description without
     * it, or null. Most descriptions are a bare Facebook link, so the sheet
     * shows it as its own row instead of a raw URL.
     */
    function extractFacebookLink(description) {
        // The raw description, as in the app: a link that sits only in an
        // href attribute counts too.
        const link = linkify(String(description || '')).find(function (segment) {
            return segment.url !== null && FACEBOOK_HOSTS.indexOf(hostOf(segment.url)) !== -1;
        });
        if (!link) {
            return null;
        }
        const textWithoutLink = stripHtml(description)
            .split(link.url)
            .join('')
            .replace(/[ \t]+\n/g, '\n')
            .replace(/\n{3,}/g, '\n\n')
            .trim();
        return { url: link.url, textWithoutLink: textWithoutLink };
    }

    // --- Share and correction ------------------------------------------------

    const APP_URL = 'https://app.gdzienawesta.com';

    function localeOf(lang) {
        return lang === 'pl' ? 'pl-PL' : 'en-US';
    }

    function fill(template, values) {
        return String(template).replace(/\{\{(\w+)\}\}/g, function (_, key) {
            return values[key] !== undefined ? values[key] : '';
        });
    }

    function timeOf(date) {
        const pad = function (n) { return String(n).padStart(2, '0'); };
        return pad(date.getHours()) + ':' + pad(date.getMinutes());
    }

    /** "piątek, 25 września 2026, 20:00–02:00"; the date alone for an all-day event. */
    function whenOf(event, lang) {
        const start = new Date(event.start);
        const day = new Intl.DateTimeFormat(localeOf(lang), {
            weekday: 'long', day: 'numeric', month: 'long', year: 'numeric',
        }).format(start);
        if (event.allDay) {
            return day;
        }
        return day + ', ' + timeOf(start) + '–' + timeOf(new Date(event.end));
    }

    /** "25 września 2026, 20:00", for a subject line. */
    function startOf(event, lang) {
        const start = new Date(event.start);
        const day = new Intl.DateTimeFormat(localeOf(lang), {
            day: 'numeric', month: 'long', year: 'numeric',
        }).format(start);
        return event.allDay ? day : day + ', ' + timeOf(start);
    }

    /**
     * Title, day and hours, the place, the city's page, then the app pointer
     * after a blank line. texts: { appLine } from translations.js.
     */
    function shareMessage(event, citySlug, lang, texts) {
        const lines = [event.title, whenOf(event, lang)];
        const location = splitLocation(event.location, '');
        if (location.place) {
            lines.push(location.street ? location.place + ', ' + location.street : location.place);
        }
        lines.push('https://' + citySlug + '.gdzienawesta.com');
        lines.push('');
        lines.push(fill(texts.appLine, { url: APP_URL }));
        return lines.join('\n');
    }

    /**
     * The address is put together here rather than written as a mailto: link
     * in the HTML: the CDN in front of the site rewrites every mailto: it finds
     * in a page into an obfuscated link plus a script of its own.
     */
    function supportEmail() {
        return ['support', 'gdzienawesta.com'].join('@');
    }

    /**
     * A pre-filled e-mail for "Suggest a correction". texts: the correction
     * dictionary from translations.js ({ subject, hello, intro, event, date,
     * city, id, appVersion }). The id and version lines appear only when
     * given - the website has neither.
     */
    function correctionMail(event, cityName, lang, texts, extra) {
        const more = extra || {};
        const lines = [
            texts.hello,
            '',
            texts.intro,
            '',
            '',
            '---',
            texts.event + ': ' + event.title,
            texts.date + ': ' + whenOf(event, lang),
            texts.city + ': ' + cityName,
        ];
        if (more.id) {
            lines.push(texts.id + ': ' + more.id);
        }
        if (more.appVersion) {
            lines.push(texts.appVersion + ': ' + more.appVersion);
        }
        return {
            to: supportEmail(),
            subject: fill(texts.subject, { title: event.title, date: startOf(event, lang) }),
            body: lines.join('\n'),
        };
    }

    function mailtoHref(mail) {
        return 'mailto:' + mail.to
            + '?subject=' + encodeURIComponent(mail.subject)
            + '&body=' + encodeURIComponent(mail.body);
    }

    const api = {
        relativeDayLabel: relativeDayLabel,
        splitLocation: splitLocation,
        stripHtml: stripHtml,
        linkify: linkify,
        extractFacebookLink: extractFacebookLink,
        shareMessage: shareMessage,
        correctionMail: correctionMail,
        mailtoHref: mailtoHref,
        supportEmail: supportEmail,
    };

    if (typeof module !== 'undefined' && module.exports) {
        module.exports = api;
    } else {
        root.GnwModel = api;
    }
})(typeof window !== 'undefined' ? window : this);
