/*
 * The map of cities on gdzienawesta.com, as pure functions: where a city
 * stands on the outline of Poland, where its label goes so that no two
 * collide, and what the date tile of a list row says.
 *
 * No framework and no build step, the same arrangement as model.js: in the
 * browser this hangs on window.GnwCities; in Node (the tests) it is the
 * module's exports. The page itself - measuring, rendering, the list - is
 * hub.js.
 *
 * Tests: tests/frontend/cities.test.js, run with node --test (see README).
 */
(function (root) {
    'use strict';

    // --- The outline and where a city stands on it --------------------------

    // Poland from Natural Earth 1:50m (public domain), 316 points, drawn in a
    // 1000 x 950 box in the Mercator projection - the one Google Maps uses, so
    // the shape is the familiar one.
    const VIEW_WIDTH = 1000;
    const VIEW_HEIGHT = 950;
    const OUTLINE = 'M931.8,553.3 937.0,564.0 939.1,572.3 937.0,578.8 937.7,585.4 942.2,592.4 956.8,613.7 964.1,634.2 968.6,642.1 979.3,652.5 980.0,656.7 975.8,660.4 972.4,660.9 969.6,662.0 967.9,665.7 970.6,669.7 974.5,675.2 979.0,691.3 978.6,704.4 975.1,707.9 970.3,715.5 967.5,722.6 942.2,727.5 936.3,735.1 922.5,749.8 913.1,758.1 899.3,773.5 877.1,799.5 869.1,810.4 863.2,819.2 845.6,842.9 840.0,853.0 841.1,861.2 847.0,880.5 848.0,889.2 847.0,897.1 845.2,904.3 845.6,907.3 850.8,912.4 859.1,920.6 859.4,923.2 858.4,926.7 855.3,929.5 844.9,926.7 833.5,921.1 829.3,921.9 823.1,920.6 797.1,909.9 779.4,901.7 777.7,896.3 774.6,888.4 766.9,882.0 750.0,876.4 742.7,871.7 715.0,869.4 702.8,869.2 694.5,871.0 689.0,871.0 681.4,882.5 676.2,885.8 668.5,886.1 662.0,884.0 655.0,878.1 644.3,874.8 636.3,876.4 630.8,875.1 625.6,874.8 623.9,875.8 620.0,875.8 614.2,878.7 607.9,882.8 600.6,885.8 595.4,892.8 590.6,905.8 577.1,899.9 572.6,902.5 566.0,904.3 561.5,902.5 562.5,897.9 564.6,892.8 564.6,885.6 563.2,877.6 559.1,875.1 552.8,874.0 549.4,872.5 549.0,869.9 545.9,866.6 540.4,858.1 534.8,847.6 531.4,844.2 526.2,849.4 517.8,855.0 513.0,857.1 503.3,873.5 485.6,874.0 484.6,866.3 482.9,859.1 472.8,857.1 472.5,852.7 470.4,841.9 449.9,820.5 447.2,811.4 448.2,808.0 446.8,802.3 442.3,799.0 426.0,794.8 421.9,797.1 418.1,794.8 412.2,789.6 402.1,785.5 401.1,783.1 397.3,779.5 395.2,779.0 394.2,781.3 391.0,784.4 380.6,788.6 376.5,786.8 372.7,783.4 368.2,775.8 361.9,769.3 356.7,767.0 353.6,763.3 352.9,760.7 364.7,755.2 367.1,749.8 365.8,739.6 364.0,738.3 359.5,741.7 349.8,744.5 340.8,746.1 336.3,746.1 311.0,727.5 294.4,721.8 284.7,720.2 283.6,722.0 288.1,732.5 295.8,745.3 295.4,748.7 286.4,753.9 281.2,756.3 275.0,760.7 269.8,767.0 265.6,769.6 261.5,769.1 257.7,765.9 246.9,746.9 233.8,732.5 232.4,729.1 228.2,728.3 222.3,725.2 220.2,720.5 223.4,716.0 227.2,711.5 234.4,708.9 236.5,706.5 237.9,702.9 240.3,697.9 239.6,696.3 234.8,690.8 227.2,685.5 206.4,689.4 200.8,692.1 197.7,688.7 195.3,683.1 189.8,682.3 182.8,677.3 174.2,672.6 165.9,671.3 148.5,664.4 141.9,664.1 138.1,661.7 134.0,656.4 130.5,650.9 128.8,639.2 116.0,634.2 103.1,630.7 102.5,632.6 102.8,644.0 102.1,650.4 93.8,654.1 85.5,654.6 86.2,652.5 95.9,631.8 100.4,618.5 105.6,594.3 99.3,575.0 97.6,566.2 94.8,561.9 77.5,552.5 76.1,549.3 78.9,536.4 77.5,531.0 73.4,525.3 67.8,514.3 65.4,504.5 72.7,493.2 74.4,485.1 77.5,473.7 79.6,467.4 79.9,465.5 75.4,461.2 74.4,454.9 75.4,445.9 73.0,439.1 66.8,435.0 63.0,429.3 60.9,421.9 62.6,410.6 67.1,395.3 57.1,376.9 32.1,355.1 20.0,339.9 21.0,331.0 26.2,323.2 35.9,316.0 43.2,303.5 47.0,288.5 47.4,285.7 47.7,274.8 36.3,230.8 34.6,219.8 33.2,206.3 32.5,202.6 54.6,211.9 63.7,217.3 62.6,211.3 60.9,206.3 61.9,198.6 61.2,187.3 41.5,181.7 28.3,179.7 26.6,171.7 28.0,166.6 31.8,169.8 44.6,170.9 76.5,155.6 131.6,135.6 190.5,116.8 204.3,114.8 218.2,110.8 223.0,103.9 228.2,99.0 236.2,86.7 253.9,67.1 285.4,60.2 297.2,51.0 321.4,38.0 377.5,23.5 400.7,20.3 423.6,20.0 444.0,31.3 465.5,45.5 469.7,54.1 457.9,48.7 440.9,35.9 434.7,35.4 449.2,74.0 456.9,87.5 473.2,97.9 486.7,101.0 527.9,95.0 542.8,87.0 546.9,82.9 550.8,85.0 577.8,87.0 605.1,89.3 649.1,91.6 694.9,94.1 742.3,96.7 793.6,99.3 848.0,101.0 851.1,99.9 856.7,93.3 863.6,94.1 871.6,98.2 875.4,101.3 876.8,104.8 877.8,108.5 882.3,109.3 890.3,112.2 901.0,119.1 909.3,125.6 917.3,135.1 920.1,145.6 920.1,157.5 919.7,165.2 920.4,168.3 931.5,223.7 949.9,276.7 956.4,302.4 959.2,316.0 961.3,335.4 962.0,349.3 962.0,357.0 960.6,367.5 955.1,373.8 920.1,391.7 913.1,397.2 903.1,411.2 893.4,425.4 891.3,430.3 890.6,433.4 892.7,438.3 905.2,445.6 918.0,451.9 922.1,456.5 931.2,462.2 934.6,467.4 936.7,472.0 936.3,482.6 932.2,497.2 933.9,508.1 929.8,515.3 926.3,523.4 925.6,537.7 931.8,553.3Z';

    // The projection the outline was drawn with. x grows with longitude and y
    // with the Mercator ordinate, both at the same scale, which is what makes
    // the projection conformal. Recovered from the drawing by fitting it to
    // the ten cities it was made with; every one of them lands within a unit
    // of its place, at a map a thousand units wide.
    const SCALE = 96.2319;           // units per degree
    const WEST = 13.91948;           // longitude at x = 0
    const NORTH_ORDINATE = 66.05738; // Mercator ordinate (in degrees) at y = 0

    function mercatorOrdinate(latitude) {
        const phi = latitude * Math.PI / 180;
        return Math.log(Math.tan(Math.PI / 4 + phi / 2)) * 180 / Math.PI;
    }

    /**
     * A city's place on the map in view units, { x, y }, or null for a city
     * without coordinates: it is listed, it just has no dot.
     */
    function project(latitude, longitude) {
        if (latitude == null || longitude == null) return null;
        return {
            x: SCALE * (longitude - WEST),
            y: SCALE * (NORTH_ORDINATE - mercatorOrdinate(latitude)),
        };
    }

    /** The same place in percent of the map's width and height, for CSS. */
    function projectPercent(latitude, longitude) {
        const point = project(latitude, longitude);
        if (!point) return null;
        return { left: point.x / VIEW_WIDTH * 100, top: point.y / VIEW_HEIGHT * 100 };
    }

    function outlinePoints() {
        return OUTLINE.slice(1).split(' ').map(pair => pair.split(',').map(Number));
    }

    /** Whether a point in view units lies inside the outline (ray casting). */
    function insideOutline(x, y) {
        const points = outlinePoints();
        let inside = false;
        for (let i = 0, j = points.length - 1; i < points.length; j = i++) {
            const [xi, yi] = points[i];
            const [xj, yj] = points[j];
            if ((yi > y) !== (yj > y) && x < (xj - xi) * (y - yi) / (yj - yi) + xi) {
                inside = !inside;
            }
        }
        return inside;
    }

    // --- Labels -------------------------------------------------------------

    // A label may stand right of its dot, left, above or below, or on one of
    // the four diagonals. Offsets are from the dot's centre, in pixels, and
    // match the positions styles.css gives each [data-side].
    const DOT_RADIUS = 7;
    const LABEL_GAP = 1.5;
    const PASSES = 300;

    function labelRect(item, side) {
        const { x, y, w, h } = item;
        switch (side) {
            case 'r': return [x + 10, y - h / 2, w, h];
            case 'l': return [x - 10 - w, y - h / 2, w, h];
            case 't': return [x - w / 2, y - 11 - h, w, h];
            case 'b': return [x - w / 2, y + 11, w, h];
            case 'tr': return [x + 4, y - 5 - h, w, h];
            case 'tl': return [x - 4 - w, y - 5 - h, w, h];
            case 'br': return [x + 4, y + 5, w, h];
            case 'bl': return [x - 4 - w, y + 5, w, h];
        }
        return null;
    }

    function overlaps(a, b, margin) {
        return a[0] < b[0] + b[2] + margin && b[0] < a[0] + a[2] + margin
            && a[1] < b[1] + b[3] + margin && b[1] < a[1] + a[3] + margin;
    }

    /**
     * Where each label goes: an array of sides ('r', 'tl', ...) or 'none' for a
     * label that fits nowhere - its dot stays, and its city is on the list.
     *
     * items: [{ x, y, w, h }] in pixels - the dot's centre and the label's
     * measured size. width, height: the map's size in pixels.
     *
     * A label never covers another dot or label and never leaves the map. A
     * city near the edge starts with the side nearer the middle (Szczecin to
     * the right, Rzeszów to the left). One greedy pass, most crowded cities
     * first, turned out fragile: at 320 px it hid Warsaw and Rzeszów, at 390
     * px Kraków. So the pass is repeated in a few hundred shuffled orders and
     * the layout hiding the fewest labels wins, then the one closest to every
     * label on its first choice. The shuffle is seeded, so every visit gets
     * the same layout; on sizes measured once, the whole thing takes a
     * fraction of a millisecond.
     */
    function placeLabels(items, width, height) {
        const within = a => a[0] >= -2 && a[1] >= -2
            && a[0] + a[2] <= width + 2 && a[1] + a[3] <= height + 2;
        const dots = items.map(it => [it.x - DOT_RADIUS, it.y - DOT_RADIUS, 2 * DOT_RADIUS, 2 * DOT_RADIUS]);
        const preferences = items.map(it => {
            const fx = it.x / width;
            if (fx > 0.72) return ['l', 't', 'b', 'tl', 'bl', 'r', 'tr', 'br'];
            if (fx < 0.28) return ['r', 't', 'b', 'tr', 'br', 'l', 'tl', 'bl'];
            return ['r', 'l', 't', 'b', 'tr', 'tl', 'br', 'bl'];
        });

        const greedy = order => {
            const placed = [];
            const sides = new Array(items.length).fill('none');
            let score = 0;
            for (const i of order) {
                let rank = 0;
                for (const side of preferences[i]) {
                    const rect = labelRect(items[i], side);
                    if (within(rect)
                        && !placed.some(other => overlaps(rect, other, LABEL_GAP))
                        && !dots.some((dot, j) => j !== i && overlaps(rect, dot, 1))) {
                        sides[i] = side;
                        placed.push(rect);
                        break;
                    }
                    rank++;
                }
                score += sides[i] === 'none' ? 1000 : rank;
            }
            return { sides, score };
        };

        const crowding = i => items.reduce((sum, it, j) => j === i ? sum
            : sum + 1 / Math.max(Math.hypot(it.x - items[i].x, it.y - items[i].y), 1), 0);
        let order = items.map((_, i) => i).sort((a, b) => crowding(b) - crowding(a) || a - b);
        let best = greedy(order);

        let seed = 7;
        const random = () => (seed = (seed * 16807) % 2147483647) / 2147483647;
        for (let n = 0; n < PASSES && best.score > 0; n++) {
            order = order.slice();
            for (let k = order.length - 1; k > 0; k--) {
                const j = Math.floor(random() * (k + 1));
                [order[k], order[j]] = [order[j], order[k]];
            }
            const next = greedy(order);
            if (next.score < best.score) best = next;
        }
        return best.sides;
    }

    // --- The date tile of a list row ----------------------------------------

    function localDayNumber(date) {
        // A calendar day in the visitor's time zone, so a daylight-saving
        // change does not turn a day into 23 or 25 hours.
        return Date.UTC(date.getFullYear(), date.getMonth(), date.getDate()) / 86400000;
    }

    /**
     * What the tile above the day of the month says, as data:
     * { kind: 'today' } for today, and for an event that began earlier and has
     * not ended; { kind: 'weekday', index } within the week, index as
     * Date#getDay(); { kind: 'month', index } further out, index as
     * Date#getMonth(). day is the day of the month.
     */
    function dateTile(start, now) {
        const date = new Date(start);
        const days = localDayNumber(date) - localDayNumber(now);
        const day = date.getDate();
        if (days <= 0) return { kind: 'today', day };
        if (days < 7) return { kind: 'weekday', index: date.getDay(), day };
        return { kind: 'month', index: date.getMonth(), day };
    }

    const api = {
        VIEW_WIDTH: VIEW_WIDTH,
        VIEW_HEIGHT: VIEW_HEIGHT,
        OUTLINE: OUTLINE,
        project: project,
        projectPercent: projectPercent,
        insideOutline: insideOutline,
        labelRect: labelRect,
        placeLabels: placeLabels,
        dateTile: dateTile,
    };

    if (typeof module !== 'undefined' && module.exports) {
        module.exports = api;
    } else {
        root.GnwCities = api;
    }
})(typeof window !== 'undefined' ? window : this);
