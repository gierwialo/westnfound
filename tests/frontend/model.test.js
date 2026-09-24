'use strict';

// From the repository root: node --test 'tests/**/*.test.js'
// Cases follow the mobile app's tests for the same functions. Dates are built
// in local time, so the results do not depend on the machine's time zone.

const { test } = require('node:test');
const assert = require('node:assert/strict');
const model = require('../../frontend/model.js');

const at = (y, m, d, h = 0, min = 0) => new Date(y, m - 1, d, h, min);
const event = (start, end, extra = {}) => ({
    title: 'Sobotnie WCS party',
    start: start.toISOString(),
    end: end.toISOString(),
    location: 'Solec 38, 00-394 Warszawa, Poland',
    description: '',
    ...extra,
});

// --- Day badge ---------------------------------------------------------------

test('an event under way is "now"', () => {
    const e = event(at(2026, 9, 19, 20), at(2026, 9, 20, 0));
    assert.deepEqual(model.relativeDayLabel(e, at(2026, 9, 19, 21)), { kind: 'now' });
});

test('later today, tomorrow, and days ahead with the weekday', () => {
    const now = at(2026, 9, 19, 16);
    assert.deepEqual(model.relativeDayLabel(event(at(2026, 9, 19, 20), at(2026, 9, 20, 0)), now), { kind: 'today' });
    assert.deepEqual(model.relativeDayLabel(event(at(2026, 9, 20, 18), at(2026, 9, 20, 22)), now), { kind: 'tomorrow' });
    assert.deepEqual(
        model.relativeDayLabel(event(at(2026, 9, 25, 20), at(2026, 9, 26, 2)), now),
        { kind: 'inDays', weekday: 5, days: 6 });
});

test('tomorrow is a calendar day, not 24 hours', () => {
    // 23:30 today, the event at 00:30: one hour away, but tomorrow.
    const e = event(at(2026, 9, 20, 0, 30), at(2026, 9, 20, 3));
    assert.deepEqual(model.relativeDayLabel(e, at(2026, 9, 19, 23, 30)), { kind: 'tomorrow' });
});

test('days are counted across the change to winter time', () => {
    const e = event(at(2026, 10, 27, 20), at(2026, 10, 27, 23));
    assert.deepEqual(model.relativeDayLabel(e, at(2026, 10, 24, 12)), { kind: 'inDays', weekday: 2, days: 3 });
});

// --- Address -----------------------------------------------------------------

test('the venue and the street; postcode, town and country dropped', () => {
    assert.deepEqual(
        model.splitLocation('Tango Milonga, Wybrzeże Kościuszkowskie 21A, 00-390 Warszawa, Poland', 'Warszawa'),
        { place: 'Tango Milonga', street: 'Wybrzeże Kościuszkowskie 21A', streetWithCity: 'Wybrzeże Kościuszkowskie 21A, Warszawa' });
});

test('a second segment that is the postcode or the country is not a street', () => {
    assert.equal(model.splitLocation('Solec 38, 00-394 Warszawa, Poland', 'Warszawa').street, '');
    assert.equal(model.splitLocation('Klub, Polska', 'Łódź').street, '');
    assert.equal(model.splitLocation('Klub, Polska', 'Łódź').place, 'Klub');
});

test('no location, no address', () => {
    assert.deepEqual(model.splitLocation('', 'Kraków'), { place: '', street: '', streetWithCity: '' });
    assert.deepEqual(model.splitLocation(undefined, 'Kraków'), { place: '', street: '', streetWithCity: '' });
});

// --- Description -------------------------------------------------------------

test('HTML becomes text: breaks kept, tags dropped, entities decoded', () => {
    assert.equal(model.stripHtml('Wstęp <b>wolny</b><br>Tom &amp; Jerry&nbsp;!'), 'Wstęp wolny\nTom & Jerry !');
    assert.equal(model.stripHtml('<p>a</p><p>b</p>'), 'a\nb');
});

test('a script in the description ends up as harmless text', () => {
    const text = model.stripHtml('<script>alert(1)</script><img src=x onerror=alert(2)>Hej');
    assert.doesNotMatch(text, /</);
    assert.equal(text, 'alert(1)Hej');
});

test('links are http(s) only, trailing punctuation stays plain', () => {
    assert.deepEqual(model.linkify('Zapisy: https://example.com/a. Do zobaczenia!'), [
        { text: 'Zapisy: ', url: null },
        { text: 'https://example.com/a', url: 'https://example.com/a' },
        { text: '. Do zobaczenia!', url: null },
    ]);
    assert.deepEqual(model.linkify('javascript:alert(1)'), [{ text: 'javascript:alert(1)', url: null }]);
});

test('the Facebook link comes out of the description', () => {
    assert.deepEqual(
        model.extractFacebookLink('https://www.facebook.com/events/123/\n\nWstęp 20 zł'),
        { url: 'https://www.facebook.com/events/123/', textWithoutLink: 'Wstęp 20 zł' });
    assert.deepEqual(
        model.extractFacebookLink('<a href="https://fb.me/e/abc">wydarzenie</a>'),
        { url: 'https://fb.me/e/abc', textWithoutLink: 'wydarzenie' });
});

test('no Facebook link, no row', () => {
    assert.equal(model.extractFacebookLink('https://example.com only'), null);
    assert.equal(model.extractFacebookLink(''), null);
});

// --- Share and correction ----------------------------------------------------

const PL = {
    appLine: 'Gdzie na Westa? na iOS i Androida: {{url}}',
    correction: {
        subject: 'Poprawka: {{title}}, {{date}}',
        hello: 'Cześć!',
        intro: 'Coś się nie zgadza w tym wydarzeniu:',
        event: 'Wydarzenie',
        date: 'Data',
        city: 'Miasto',
        id: 'Identyfikator',
        appVersion: 'Wersja aplikacji',
    },
};

test('the share text: title, when, place, city page, app line', () => {
    const e = event(at(2026, 9, 25, 20), at(2026, 9, 26, 2),
        { title: 'Piątkowe party', location: 'Tango Milonga, Wybrzeże Kościuszkowskie 21A, 00-390 Warszawa, Poland' });
    assert.equal(model.shareMessage(e, 'warszawa', 'pl', PL), [
        'Piątkowe party',
        'piątek, 25 września 2026, 20:00–02:00',
        'Tango Milonga, Wybrzeże Kościuszkowskie 21A',
        'https://warszawa.gdzienawesta.com',
        '',
        'Gdzie na Westa? na iOS i Androida: https://app.gdzienawesta.com',
    ].join('\n'));
});

test('the share text in English, and without a location', () => {
    const e = event(at(2026, 9, 25, 20), at(2026, 9, 26, 2), { title: 'Friday party', location: '' });
    const text = model.shareMessage(e, 'lodz', 'en', { appLine: 'Gdzie na Westa? for iOS and Android: {{url}}' });
    assert.equal(text.split('\n')[1], 'Friday, September 25, 2026, 20:00–02:00');
    assert.equal(text.split('\n')[2], 'https://lodz.gdzienawesta.com');
});

test('the correction mail: address built in the script, event under the rule', () => {
    const e = event(at(2026, 9, 25, 20), at(2026, 9, 26, 2), { title: 'Piątkowe party' });
    const mail = model.correctionMail(e, 'Warszawa', 'pl', PL.correction);
    assert.equal(mail.to, 'support@gdzienawesta.com');
    assert.equal(mail.subject, 'Poprawka: Piątkowe party, 25 września 2026, 20:00');
    assert.equal(mail.body, [
        'Cześć!', '', 'Coś się nie zgadza w tym wydarzeniu:', '', '', '---',
        'Wydarzenie: Piątkowe party',
        'Data: piątek, 25 września 2026, 20:00–02:00',
        'Miasto: Warszawa',
    ].join('\n'));
    assert.match(model.mailtoHref(mail), /^mailto:support@gdzienawesta\.com\?subject=Poprawka%3A%20/);
});

test('the id and version lines appear only when given', () => {
    const e = event(at(2026, 9, 25, 20), at(2026, 9, 26, 2));
    const body = model.correctionMail(e, 'Warszawa', 'pl', PL.correction, { id: 'abc', appVersion: '1.2.0' }).body;
    assert.match(body, /Identyfikator: abc\nWersja aplikacji: 1\.2\.0$/);
});

test('the page source never carries the support address as text', () => {
    // It is joined at run time; a literal would be rewritten by the CDN.
    const source = require('node:fs').readFileSync(require.resolve('../../frontend/model.js'), 'utf8');
    assert.doesNotMatch(source, /support@gdzienawesta/);
});

// --- The map of cities and the way back to it ----------------------------------

test('the map is on the apex of whatever domain the page is on', () => {
    assert.equal(model.hubHref('lodz.gdzienawesta.com'), '//gdzienawesta.com/');
    assert.equal(model.hubHref('gdansk.gdzienawesta.com'), '//gdzienawesta.com/');
    assert.equal(model.hubHref('lodz.lvh.me'), '//lvh.me/');
    // Nowhere better to go than this host's own front page.
    assert.equal(model.hubHref('localhost'), '/');
    assert.equal(model.hubHref('127.0.0.1'), '/');
});

test('the city cookie is set for the whole domain, from the city\'s own address only', () => {
    assert.equal(
        model.cityCookie('lodz.gdzienawesta.com', 'lodz', true),
        'gnw_city=lodz; Domain=gdzienawesta.com; Path=/; Max-Age=31536000; SameSite=Lax; Secure');
    assert.equal(
        model.cityCookie('lodz.lvh.me', 'lodz', false),
        'gnw_city=lodz; Domain=lvh.me; Path=/; Max-Age=31536000; SameSite=Lax');
    // The apex, a host of another city, and a host with no city in it.
    assert.equal(model.cityCookie('gdzienawesta.com', 'warszawa', true), null);
    assert.equal(model.cityCookie('krakow.gdzienawesta.com', 'lodz', true), null);
    assert.equal(model.cityCookie('localhost', 'warszawa', false), null);
});

test('the city is read back from the cookies, and nothing else is', () => {
    assert.equal(model.cityFromCookies('_ga=GA1.1; gnw_city=krakow; x=1'), 'krakow');
    assert.equal(model.cityFromCookies('gnw_city=lodz'), 'lodz');
    assert.equal(model.cityFromCookies('xgnw_city=lodz'), null);
    assert.equal(model.cityFromCookies('gnw_city=<script>'), null);
    assert.equal(model.cityFromCookies(''), null);
});
