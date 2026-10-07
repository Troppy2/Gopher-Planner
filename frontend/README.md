# Frontend

React + TypeScript + Vite single-page app for Gopher Planner. Styling follows `docs/design-rules.md` (maroon #7A0019, gold #FFCC33, ivory #E6E0D2). See `docs/Gopher Planner Frontend Technical Design.md`.

Import rule (downward only): `screens` -> `features` -> `ui`. Screens never import each other.

## Run

```bash
cd frontend
npm install
npm run dev        # http://localhost:5173
npm run build      # typecheck + production build
```

Walkthrough: `/login` → Continue with Google → onboarding (coursework, profile, plan building) → dashboard, flow chart, catalog, settings.

Dev-only "Preview only" controls (dashed boxes) force states the mock can't reach by itself: a scanned PDF, a non-UMN account, a catalog error, a failed save. **Settings → Reset demo data** clears everything and returns you to login.

## Mock data (temporary)

The backend isn't ready yet, so every screen reads from fake data:

- `src/api/mock/seed.json` holds the seeded profile, summary, plan, courses, and options.
- `src/api/mock/mockDb.ts` keeps an in-memory copy, saved to `localStorage` (`gp-mock-db`) so a refresh keeps your progress.
- `src/api/endpoints.ts` holds the only functions screens call. They're named after the API endpoints proposed in the tech design.

To switch to the real API:

1. Replace each function body in `src/api/endpoints.ts` with a `request()` call from `src/api/client.ts`. Keep the signatures.
2. Delete `src/api/mock/`, then delete the `mockFlags` imports and `DemoToggle` blocks in the screens.
3. Replace `src/features/auth/session.store.ts` with the real auth client.

## Structure

- `src/app/`: router, layouts (`PublicLayout`, `OnboardingLayout`, `AppShell`), and guards.
- `src/screens/`: one folder per screen, each with its own CSS.
- `src/features/`: code shared by two or more screens: plan draft and rules, the course drawer (`?course=CODE`), search, and the session.
- `src/ui/`: design-system primitives built on Radix with our own styling.
- `src/styles/`: tokens, base styles, and the app-shell layout.
