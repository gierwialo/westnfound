// Counts one click on the site: a GET /e/<action>[/<detail>] that the server
// in front of the site answers with 204 and writes to its access log, like any
// other request. No cookie, no third party, and nothing about the visitor in
// the address: the action is a fixed word, the detail says where the click
// happened (the card or the sheet, a store, a city's slug).
//
// Nothing here serves /e/, so on a copy of this site or in local work the
// request just fails, quietly, and the page does not notice.
(function (root) {
    const ACTION = /^[a-z-]{2,24}$/;
    const DETAIL = /^[a-z0-9-]{1,24}$/;

    // Returns the address it asked for, or null when the names are not
    // well-formed (a slug from the page could be anything).
    function track(action, detail, send) {
        if (!ACTION.test(action || '') || (detail != null && !DETAIL.test(detail))) return null;
        const url = '/e/' + action + (detail != null ? '/' + detail : '');
        const fetchFn = send || (typeof fetch === 'function' ? fetch : null);
        if (!fetchFn) return null;
        try {
            // keepalive: Directions and the store links take the visitor away
            // at once, and the request has to outlive the page.
            const pending = fetchFn(url, { keepalive: true, credentials: 'omit', cache: 'no-store' });
            if (pending && pending.catch) pending.catch(() => {});
        } catch (e) {
            // Counting must never be the reason a button does not work.
        }
        return url;
    }

    if (typeof module !== 'undefined' && module.exports) {
        module.exports = track;
    } else {
        root.GnwTrack = track;
    }
})(typeof window !== 'undefined' ? window : this);
