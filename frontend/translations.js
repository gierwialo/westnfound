const translations = {
    pl: {
        title: "Gdzie na Westa?",

        // Shown to search engines, not on the page. {city} is filled in only
        // when more than one city exists - see updateDescription() in app.js.
        metaDescription: "Najbliższe imprezy i warsztaty West Coast Swing — data, miejsce i odliczanie do startu.",
        metaDescriptionCity: "Najbliższe imprezy i warsztaty West Coast Swing w mieście {city} — data, miejsce i odliczanie do startu.",
        metaDescriptionCalendar: "Kalendarz wydarzeń West Coast Swing — pełna lista imprez i warsztatów, do subskrybowania w telefonie.",
        metaDescriptionCalendarCity: "Kalendarz wydarzeń West Coast Swing w mieście {city} — pełna lista imprez i warsztatów, do subskrybowania w telefonie.",

        // Home page
        upcoming: "Najbliższe",
        badgeNow: "Trwa teraz",
        badgeToday: "Dziś",
        badgeTomorrow: "Jutro",
        badgeInDays: "{weekday} · za {n} dni",
        later: "Potem",
        fullCalendar: "Pełny kalendarz",
        actionCalendar: "Do kalendarza",
        actionDirections: "Trasa",
        actionDetails: "Szczegóły",
        share: "Udostępnij",
        close: "Zamknij",
        changeCity: "Zmień miasto",
        cityTitle: "Miasto",
        cityHint: "Każde miasto ma własny adres, na przykład lodz.gdzienawesta.com.",
        description: "Opis",
        facebookEvent: "Wydarzenie na Facebooku",
        correctionTitle: "Zgłoś poprawkę",
        correctionHint: "Zły adres albo godzina? Napisz do nas",
        // Line under a shared event, and the pre-filled e-mail of "Zgłoś poprawkę".
        // The wording is the mobile app's, so the same event reads the same everywhere.
        appLine: "Gdzie na Westa? na iOS i Androida: {{url}}",
        correction: {
            subject: "Poprawka: {{title}}, {{date}}",
            hello: "Cześć!",
            intro: "Coś się nie zgadza w tym wydarzeniu:",
            event: "Wydarzenie",
            date: "Data",
            city: "Miasto"
        },
        unknownCityHeading: "Gdzie to?",
        loadFailed: "Nie udało się pobrać wydarzeń.",
        errorHint: "Sprawdź połączenie z internetem.",
        emptyTitle: "Na razie cisza",
        emptyBody: "W tym mieście nie ma teraz zaplanowanych wydarzeń. Zajrzyj później albo sprawdź inne miasta.",
        refresh: "Odśwież",
        keeperPrompt: "Prowadzisz kalendarz tego miasta?",
        keeperLink: "Zobacz, jak dodawać wydarzenia",

        // Loading & Error states
        loading: "Ładowanie wydarzenia...",
        errorTitle: "Ups! Coś poszło nie tak",
        footerCities: "Miasta:",
        unknownCityTitle: "Ojej, jeszcze nie wiemy, co się tam tańczy",
        unknownCityBody: "Może po prostu nikt nam jeszcze nie powiedział. Miasta, w których już tańczymy:",
        addYourCity: "Dodaj swoje miasto",
        errorDefault: "Błąd pobierania wydarzenia",
        retryButton: "Spróbuj ponownie",

        // Footer
        footerLove: "z miłości do Westa❤️",
        footerCode: "Kod dostępny na",
        footerFeedback: "Masz pomysł lub uwagę?",
        footerReport: "Zgłoś tutaj",
        footerCalendarDirect: "Kalendarz",
        footerApp: "Aplikacja na telefon",
        footerThanks: "Podziękowania",
        footerSupport: "❤️ Wesprzyj projekt",
        calendarPath: "kalendarz",

        // Calendar page
        calendarTitle: "Kalendarz",
        calendarSubtitle: "Wszystkie wydarzenia w jednym miejscu",
        calendarLoading: "Ładowanie kalendarza...",
        calendarSubscribe: "📅 Subskrybuj kalendarz",
        calendarCopy: "🔗 Skopiuj adres",
        calendarCopied: "✓ Skopiowano",
        calendarOpenGoogle: "Otwórz w Google Calendar",
        calendarSubscribeHint: "Dodaj ten kalendarz do telefonu albo komputera — nowe wydarzenia będą się w nim pojawiać same.",
        calendarBackToEvents: "← Najbliższe wydarzenia",

        // Language
        language: "Język",
        languageName: "Polski",

        // Timezone
        timezone: "Czasy wyświetlane w Twojej lokalnej strefie czasowej"
    },
    en: {
        title: "Where to West?",

        // Shown to search engines, not on the page. {city} is filled in only
        // when more than one city exists - see updateDescription() in app.js.
        metaDescription: "Upcoming West Coast Swing parties and workshops - date, venue and a countdown to the start.",
        metaDescriptionCity: "Upcoming West Coast Swing parties and workshops in {city} - date, venue and a countdown to the start.",
        metaDescriptionCalendar: "West Coast Swing event calendar - every party and workshop, ready to subscribe to on your phone.",
        metaDescriptionCalendarCity: "West Coast Swing event calendar for {city} - every party and workshop, ready to subscribe to on your phone.",

        // Home page
        upcoming: "Upcoming",
        badgeNow: "Happening now",
        badgeToday: "Today",
        badgeTomorrow: "Tomorrow",
        badgeInDays: "{weekday} · in {n} days",
        later: "Coming up",
        fullCalendar: "Full calendar",
        actionCalendar: "Add to calendar",
        actionDirections: "Directions",
        actionDetails: "Details",
        share: "Share",
        close: "Close",
        changeCity: "Change city",
        cityTitle: "City",
        cityHint: "Each city has its own address, for example lodz.gdzienawesta.com.",
        description: "Description",
        facebookEvent: "Event on Facebook",
        correctionTitle: "Suggest a correction",
        correctionHint: "Wrong address or time? Let us know",
        appLine: "Gdzie na Westa? for iOS and Android: {{url}}",
        correction: {
            subject: "Correction: {{title}}, {{date}}",
            hello: "Hi!",
            intro: "Something is wrong with this event:",
            event: "Event",
            date: "Date",
            city: "City"
        },
        unknownCityHeading: "Where's that?",
        loadFailed: "Couldn't load events.",
        errorHint: "Check your internet connection.",
        emptyTitle: "All quiet for now",
        emptyBody: "There are no upcoming events in this city right now. Check back later or try another city.",
        refresh: "Refresh",
        keeperPrompt: "Run this city's calendar?",
        keeperLink: "See how to add events",

        // Loading & Error states
        loading: "Loading event...",
        errorTitle: "Oops! Something went wrong",
        footerCities: "Cities:",
        unknownCityTitle: "Oh! We don't know what's dancing there yet",
        unknownCityBody: "Maybe nobody has told us yet. Cities we're already dancing in:",
        addYourCity: "Add your city (in Polish)",
        errorDefault: "Error loading event",
        retryButton: "Try again",

        // Footer
        footerLove: "with love to West❤️",
        footerCode: "Code available on",
        footerFeedback: "Have an idea or feedback?",
        footerReport: "Report here",
        footerCalendarDirect: "Calendar",
        footerApp: "Mobile app",
        footerThanks: "Thanks",
        footerSupport: "❤️ Support the project",
        calendarPath: "calendar",

        // Calendar page
        calendarTitle: "Calendar",
        calendarSubtitle: "Every event in one place",
        calendarLoading: "Loading calendar...",
        calendarSubscribe: "📅 Subscribe to calendar",
        calendarCopy: "🔗 Copy address",
        calendarCopied: "✓ Copied",
        calendarOpenGoogle: "Open in Google Calendar",
        calendarSubscribeHint: "Add this calendar to your phone or computer — new events will keep showing up on their own.",
        calendarBackToEvents: "← Upcoming events",

        // Language
        language: "Language",
        languageName: "English",

        // Timezone
        timezone: "Times displayed in your local timezone"
    }
};
