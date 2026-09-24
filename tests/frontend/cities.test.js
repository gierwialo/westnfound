'use strict';

// From the repository root: node --test 'tests/**/*.test.js'

const { test } = require('node:test');
const assert = require('node:assert/strict');
const cities = require('../../frontend/cities.js');

// The cities served when the map arrived, with the coordinates the migration
// gives them (backend/events/migrations/0004_city_coordinates.py).
const PRODUCTION = {
    Bydgoszcz: [53.1235, 18.0084],
    Gliwice: [50.2945, 18.6714],
    Katowice: [50.2649, 19.0238],
    'Kraków': [50.0614, 19.9366],
    'Łódź': [51.7592, 19.456],
    'Poznań': [52.4064, 16.9252],
    'Rzeszów': [50.0412, 21.9991],
    Szczecin: [53.4285, 14.5528],
    Warszawa: [52.2297, 21.0122],
    'Wrocław': [51.1079, 17.0385],
};

// --- Projection --------------------------------------------------------------

test('every city we serve lands inside the outline of Poland', () => {
    for (const [name, [lat, lon]] of Object.entries(PRODUCTION)) {
        const { x, y } = cities.project(lat, lon);
        assert.ok(cities.insideOutline(x, y), `${name} at ${x.toFixed(1)}, ${y.toFixed(1)}`);
    }
});

test('the cities stand where the mockup drew them', () => {
    // Positions from docs/Assets/web-city-map-2026-09/board.html, drawn
    // over the same outline. Within two units of a thousand-unit map.
    const board = { Warszawa: [682.5, 442.4], Szczecin: [60.8, 251.5], 'Rzeszów': [777.4, 778.1] };
    for (const [name, [bx, by]] of Object.entries(board)) {
        const { x, y } = cities.project(...PRODUCTION[name]);
        assert.ok(Math.hypot(x - bx, y - by) < 2, `${name}: ${x.toFixed(1)}, ${y.toFixed(1)}`);
    }
});

test('the compass points the right way', () => {
    const at = name => cities.project(...PRODUCTION[name]);
    assert.ok(at('Szczecin').x < at('Warszawa').x, 'west is left');
    assert.ok(at('Szczecin').y < at('Kraków').y, 'north is up');
});

test('a point abroad is outside, and a city without coordinates has no place', () => {
    const berlin = cities.project(52.52, 13.405);
    assert.equal(cities.insideOutline(berlin.x, berlin.y), false);
    assert.equal(cities.project(null, null), null);
    assert.equal(cities.projectPercent(52.2297, null), null);
});

test('percent positions scale with the map', () => {
    const { left, top } = cities.projectPercent(...PRODUCTION.Warszawa);
    assert.ok(Math.abs(left - 68.25) < 0.2 && Math.abs(top - 46.57) < 0.2, `${left}, ${top}`);
});

// --- Labels ------------------------------------------------------------------

// A label's size without a browser: an average bold glyph plus the padding in
// styles.css. Rough on purpose, and rounded up, so a pass here is not luck.
function labelSize(name, mapWidth) {
    if (mapWidth < 320) return { w: Math.ceil(name.length * 7.3 + 10), h: 18 };  // .narrow, 12 px
    if (mapWidth >= 560) return { w: Math.ceil(name.length * 8.6 + 12), h: 22 }; // 14 px from 600 px
    return { w: Math.ceil(name.length * 8 + 12), h: 21 };                        // 13 px
}

// Map width for each page width: the page's side padding and the map card's.
const MAP_WIDTH = { 320: 268, 390: 338, 820: 580, 1280: 487 };

for (const [page, width] of Object.entries(MAP_WIDTH)) {
    test(`all ten labels fit, apart and on the map, on a ${page} px page`, () => {
        const height = width * cities.VIEW_HEIGHT / cities.VIEW_WIDTH;
        const items = Object.entries(PRODUCTION).map(([name, [lat, lon]]) => {
            const { left, top } = cities.projectPercent(lat, lon);
            return { name, x: left / 100 * width, y: top / 100 * height, ...labelSize(name, width) };
        });
        const sides = cities.placeLabels(items, width, height);

        const rects = sides.map((side, i) => {
            assert.notEqual(side, 'none', `${items[i].name} was hidden`);
            return cities.labelRect(items[i], side);
        });
        rects.forEach((a, i) => {
            assert.ok(a[0] >= -2 && a[1] >= -2 && a[0] + a[2] <= width + 2 && a[1] + a[3] <= height + 2,
                `${items[i].name} leaves the map`);
            rects.forEach((b, j) => {
                if (j <= i) return;
                const apart = a[0] + a[2] <= b[0] || b[0] + b[2] <= a[0]
                    || a[1] + a[3] <= b[1] || b[1] + b[3] <= a[1];
                assert.ok(apart, `${items[i].name} overlaps ${items[j].name}`);
            });
            items.forEach((dot, j) => {
                if (j === i) return;
                const clear = a[0] > dot.x + 7 || a[0] + a[2] < dot.x - 7
                    || a[1] > dot.y + 7 || a[1] + a[3] < dot.y - 7;
                assert.ok(clear, `${items[i].name} covers the dot of ${dot.name}`);
            });
        });
    });
}

test('the layout is the same on every visit', () => {
    const items = Object.values(PRODUCTION).map(([lat, lon]) => {
        const { left, top } = cities.projectPercent(lat, lon);
        return { x: left / 100 * 338, y: top / 100 * 321, w: 70, h: 21 };
    });
    assert.deepEqual(cities.placeLabels(items, 338, 321), cities.placeLabels(items, 338, 321));
});

test('a label with nowhere to go is hidden, not stacked', () => {
    // Two dots on top of each other in a map barely larger than a label.
    const items = [{ x: 30, y: 15, w: 50, h: 20 }, { x: 31, y: 15, w: 50, h: 20 }];
    assert.ok(cities.placeLabels(items, 60, 30).includes('none'));
});

// --- Date tile -----------------------------------------------------------------

const at = (y, m, d, h = 0, min = 0) => new Date(y, m - 1, d, h, min);

test('today, a weekday within the week, a month further out', () => {
    const now = at(2026, 9, 22, 17);
    assert.deepEqual(cities.dateTile(at(2026, 9, 22, 21).toISOString(), now), { kind: 'today', day: 22 });
    assert.deepEqual(cities.dateTile(at(2026, 9, 26, 19).toISOString(), now), { kind: 'weekday', index: 6, day: 26 });
    assert.deepEqual(cities.dateTile(at(2026, 10, 10, 21).toISOString(), now), { kind: 'month', index: 9, day: 10 });
});

test('the seventh day ahead is a month, so a weekday never means next week', () => {
    const now = at(2026, 9, 22, 17);
    assert.equal(cities.dateTile(at(2026, 9, 28, 20).toISOString(), now).kind, 'weekday');
    assert.equal(cities.dateTile(at(2026, 9, 29, 20).toISOString(), now).kind, 'month');
});

test('an event that began last night and is still on counts as today', () => {
    const now = at(2026, 9, 23, 0, 30);
    assert.equal(cities.dateTile(at(2026, 9, 22, 21).toISOString(), now).kind, 'today');
});
