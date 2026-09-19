// What the pages with sheets (the home page and the calendar) share: which
// sheet is open, where focus goes when it opens and when it closes, and keeping
// Tab inside it. Spread into an Alpine component:
//
//     return { ...sheetsMixin(), ... };
//
// A component that needs to react when its sheet closes defines
// onSheetClosed(). The markup gives the dialog x-ref="sheetBox" and tabindex="-1".
function sheetsMixin() {
    return {
        // The open sheet: null, or the name the page gave it.
        sheet: null,
        returnFocus: null,

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
            document.documentElement.classList.remove('sheet-open');
            if (this.onSheetClosed) this.onSheetClosed();
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
    };
}
