const translations = {
    pl: {
        title: "Gdzie na Westa?",

        // Shown to search engines, not on the page. {city} is filled in only
        // when more than one city exists - see updateDescription() in app.js.
        metaDescription: "Najbliższe imprezy i praktisy West Coast Swing — data, miejsce i odliczanie do startu.",
        metaDescriptionCity: "Najbliższe imprezy i praktisy West Coast Swing w mieście {city} — data, miejsce i odliczanie do startu.",
        metaDescriptionCalendar: "Kalendarz wydarzeń West Coast Swing — pełna lista imprez i praktisów, do subskrybowania w telefonie.",
        metaDescriptionCalendarCity: "Kalendarz wydarzeń West Coast Swing w mieście {city} — pełna lista imprez i praktisów, do subskrybowania w telefonie.",
        // The map of cities on gdzienawesta.com; {count} is how many there are.
        metaDescriptionHub: "Imprezy i praktisy West Coast Swing w {count} miastach w Polsce — kiedy, gdzie i ile zostało do startu.",

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
        footerCities: "Miasta:",
        unknownCityTitle: "Ojej, jeszcze nie wiemy, co się tam tańczy",
        unknownCityBody: "Może po prostu nikt nam jeszcze nie powiedział. Miasta, w których już tańczymy, są na mapie.",
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
        calendarSubscribeTitle: "Subskrybuj w telefonie",
        calendarSubscribe: "Subskrybuj kalendarz",
        calendarCopy: "Skopiuj adres",
        calendarCopied: "Skopiowano",
        calendarOpenGoogle: "Otwórz w Google Calendar",
        calendarSubscribeHint: "Dodaj ten kalendarz do telefonu albo komputera — nowe wydarzenia będą się w nim pojawiać same.",

        // Language
        language: "Język",
        languageName: "Polski",

        // Timezone
        timezone: "Czasy wyświetlane w Twojej lokalnej strefie czasowej",

        // The map of cities on gdzienawesta.com. {count} is the number of cities.
        hubHeading: "Gdzie tańczysz westa?",
        hubLead: "Imprezy i praktisy West Coast Swing z {count} miast w Polsce: kiedy, gdzie i ile zostało do startu. Wybierz swoje miasto.",
        hubMine: "Twoje miasto",
        hubMapCaption: "Dotknij miasta na mapie albo wybierz je z listy.",
        hubMapCaptionWide: "Wybierz miasto na mapie albo z listy.",
        hubCities: "Miasta",
        hubToday: "dziś",
        hubWeekdays: ["nd", "pn", "wt", "śr", "cz", "pt", "so"],
        hubMonths: ["sty", "lut", "mar", "kwi", "maj", "cze", "lip", "sie", "wrz", "paź", "lis", "gru"],
        hubHow: "Jak to działa",
        hubStepCalendarsTitle: "Kalendarze miast",
        hubStepCalendarsBody: "Imprezy i praktisy wpisują lokalni opiekunowie kalendarzy. Widzisz to samo, co oni, prosto z ich kalendarza.",
        hubStepEventTitle: "Wszystko o imprezie",
        hubStepEventBody: "Kiedy, gdzie i ile zostało do startu. Jednym dotknięciem dodasz imprezę do kalendarza albo wyznaczysz trasę.",
        hubStepRemindTitle: "Przypomnienia",
        hubStepRemindBody: "Aplikacja przypomni Ci o imprezie, a kalendarz miasta możesz zasubskrybować w telefonie.",
        hubFree: "Bez konta, bez logowania, za darmo.",
        hubAppTitle: "Mamy aplikację",
        hubAppBody: "Gdzie na Westa? na iOS i Androida: wszystkie miasta w kieszeni i przypomnienie przed imprezą.",
        hubAppStore: "Pobierz z",
        hubGooglePlay: "Pobierz z",
        hubAddTitle: "Nie ma Twojego miasta?",
        hubAddBody: "Tańczycie westa gdzie indziej? Napisz do nas: pomożemy założyć kalendarz i dodamy miasto na mapę i do aplikacji.",
        allCitiesOnMap: "Wszystkie miasta na mapie"
    },
    en: {
        title: "Where to West?",

        // Shown to search engines, not on the page. {city} is filled in only
        // when more than one city exists - see updateDescription() in app.js.
        metaDescription: "Upcoming West Coast Swing parties and practices - date, venue and a countdown to the start.",
        metaDescriptionCity: "Upcoming West Coast Swing parties and practices in {city} - date, venue and a countdown to the start.",
        metaDescriptionCalendar: "West Coast Swing event calendar - every party and practice, ready to subscribe to on your phone.",
        metaDescriptionCalendarCity: "West Coast Swing event calendar for {city} - every party and practice, ready to subscribe to on your phone.",
        metaDescriptionHub: "West Coast Swing parties and practices in {count} cities in Poland - when, where and how long until it starts.",

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
        footerCities: "Cities:",
        unknownCityTitle: "Oh! We don't know what's dancing there yet",
        unknownCityBody: "Maybe nobody has told us yet. The cities we're already dancing in are on the map.",
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
        calendarSubscribeTitle: "Subscribe on your phone",
        calendarSubscribe: "Subscribe to calendar",
        calendarCopy: "Copy address",
        calendarCopied: "Copied",
        calendarOpenGoogle: "Open in Google Calendar",
        calendarSubscribeHint: "Add this calendar to your phone or computer — new events will keep showing up on their own.",

        // Language
        language: "Language",
        languageName: "English",

        // Timezone
        timezone: "Times displayed in your local timezone",

        // The map of cities on gdzienawesta.com. {count} is the number of cities.
        hubHeading: "Where do you dance WCS?",
        hubLead: "West Coast Swing parties and practices from {count} cities in Poland: when, where and how long until it starts. Pick your city.",
        hubMine: "Your city",
        hubMapCaption: "Tap a city on the map or pick it from the list.",
        hubMapCaptionWide: "Pick a city on the map or from the list.",
        hubCities: "Cities",
        hubToday: "today",
        hubWeekdays: ["sun", "mon", "tue", "wed", "thu", "fri", "sat"],
        hubMonths: ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"],
        hubHow: "How it works",
        hubStepCalendarsTitle: "City calendars",
        hubStepCalendarsBody: "Local calendar keepers add the parties and practices. You see what they see, straight from their calendar.",
        hubStepEventTitle: "Everything about the event",
        hubStepEventBody: "When, where and how long until it starts. One tap adds it to your calendar or opens directions.",
        hubStepRemindTitle: "Reminders",
        hubStepRemindBody: "The app reminds you before the event, and you can subscribe to a city’s calendar on your phone.",
        hubFree: "No account, no sign-in, free.",
        hubAppTitle: "We have an app",
        hubAppBody: "Gdzie na Westa? on iOS and Android: every city in your pocket and a reminder before the event.",
        hubAppStore: "Download on the",
        hubGooglePlay: "Get it on",
        hubAddTitle: "Your city isn’t here?",
        hubAddBody: "Dancing West Coast Swing somewhere else? Get in touch: we’ll help set up a calendar and add your city to the map and the app.",
        allCitiesOnMap: "All cities on the map"
    }
};
