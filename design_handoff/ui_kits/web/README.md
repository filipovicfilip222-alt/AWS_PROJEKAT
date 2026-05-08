# PredZnanje — Web UI kit

A click-thru recreation of the PredZnanje web app: login → dashboard → termini search → termin detail (slot picker) → reservation confirmation → AI Tutor chat → "Moje rezervacije" list. Built as a single-page React prototype that loads via inline Babel — no build step, just open `index.html`.

## Files
- `index.html` — host page, wires up React + Babel + the three JSX scripts
- `components.jsx` — primitives: `Icon` · `Logo` · `AIMark` · `Button` · `Badge` · `Card` · `Field`/`Input`/`Select` · `Avatar` · `Header`
- `screens.jsx` — `LoginScreen` · `Dashboard` · `TerminiScreen` · `TerminCard` · `TerminDetailScreen` · `AITutorScreen` · `MyReservationsScreen`. Mock data (`TERMINI`, `SUBJECTS`, `PROFESSORS`) lives at top.
- `styles.css` — page CSS (header, hero, cards, slot grid, chat bubbles). Builds on `../../colors_and_type.css`.
- `app.jsx` — `<App />` with login state + simple route switch

## Click-thru
Login screen accepts anything; toggle Student/Profesor pill to flip the lockup mark. From the Dashboard you can:
- Click any termin card → slot picker → "Potvrdi rezervaciju" → confirmation
- Click the italic **"PitajPreZakazivanja"** nav link → AI Tutor (sample prompt pre-filled, send simulates ~1s thinking)
- Click "Moje rezervacije" → reservation list with date blocks

## Source of truth
- `frontend/src/components/Header.tsx` — sticky bar, italic featured link, user chip
- `frontend/src/app/student/page.tsx` — dashboard layout
- `frontend/src/components/SearchTermina.tsx` — search filters
- `frontend/src/components/AITutor.tsx` — chat shell, confidence badge
- `frontend/tailwind.config.ts` + `frontend/src/styles/globals.css` — token mappings

## What was simplified
- Auth uses a fake `setUser` instead of the real Cognito flow
- AI replies are canned (one mock answer + canned thinking delay)
- No real backend / GraphQL — `TERMINI` is a hardcoded array
- Slot generation is mechanical (15-minute steps), not a real schedule resolver
