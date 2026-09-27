'use strict';

// From the repository root: node --test 'tests/**/*.test.js'

const { test } = require('node:test');
const assert = require('node:assert/strict');
const track = require('../../frontend/track.js');

function recorder() {
    const calls = [];
    const send = (url, options) => { calls.push({ url, options }); return Promise.resolve(); };
    return { calls, send };
}

test('asks for /e/<action>/<detail> without cookies', () => {
    const { calls, send } = recorder();
    assert.equal(track('calendar', 'card', send), '/e/calendar/card');
    assert.equal(track('facebook', undefined, send), '/e/facebook');
    assert.deepEqual(calls.map(c => c.url), ['/e/calendar/card', '/e/facebook']);
    assert.equal(calls[0].options.credentials, 'omit');
    assert.equal(calls[0].options.keepalive, true);
});

test('refuses names that are not plain words', () => {
    const { calls, send } = recorder();
    assert.equal(track('Calendar', 'card', send), null);
    assert.equal(track('map-list', '../admin', send), null);
    assert.equal(track('map-list', 'a b', send), null);
    assert.equal(track('', null, send), null);
    assert.equal(calls.length, 0);
});

test('a failing request never throws into the page', async () => {
    assert.equal(track('share', null, () => { throw new Error('offline'); }), '/e/share');
    assert.equal(track('share', null, () => Promise.reject(new Error('404'))), '/e/share');
    await new Promise(resolve => setImmediate(resolve));   // an unhandled rejection would fail the run
});
