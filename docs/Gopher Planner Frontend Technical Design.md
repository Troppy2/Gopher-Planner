# Gopher Planner: Frontend Technical Design

Oct 5, 2026 · @Inah James

## Scope and goals

The frontend is a React and TypeScript multi-page app in which every screen is its own page, with its own URL, route, and feature module, so no screen's code or state lives inside another's.

- **Screens:** Login, three onboarding steps, and four app destinations (Dashboard, Flow chart, Course catalog, Settings).
- **Hard rule:** no page component imports another page. Screens share only the design system, the API layer, and small cross-feature stores.
- **Carried over from the design review:** solid surfaces instead of frosted glass, in-house UI primitives instead of native form elements, and an accessible semester-card flow chart with the Obsidian-style graph as a second view.
- **Out of scope here:** transcript parsing (`pdfplumber`, backend), the course and professor data set, and hosting. This doc covers only what runs in the browser.

* **Priority:** build speed over scale. Pick the simplest option that works for one university's students, and revisit a choice only when a measured limit appears.

## Tech stack and installation

The stack is Vite, React, and strict TypeScript, with React Router for one-route-per-screen navigation and Radix primitives wrapped in our own components.

| Concern | Choice | Why |
| --- | --- | --- |
| Build | Vite, React, TypeScript (strict) | Matches the README scaffold; fast dev server |
| Routing | React Router (data router, lazy routes) | One route per screen, code-split per screen, route guards |
| Server state | TanStack Query | Caching, retries, loading and error states for every fetch |
| Client state | Zustand | Small stores for the draft plan, settings form, and UI |
| Forms and validation | React Hook Form and Zod | Typed forms; one schema shared by form and API types |
| Styling | Tailwind CSS v4 with CSS variables as tokens | Tokens live in one file; no component-library look |
| UI primitives | Radix UI (unstyled) wrapped by our own components | Accessible select, dialog, checkbox, radio, tooltip without native widgets |
| Icons | lucide-react | One consistent icon set; each icon is a React component imported by name, so unused icons stay out of the bundle |
| Graph | d3-force, d3-zoom, own canvas renderer | Obsidian-style layout and full control of drawing |
| Auth | Better Auth client | Google OAuth limited to @umn.edu, per the README |
| Tests | Vitest, Testing Library, MSW, Playwright | Unit, component, mocked API, and end-to-end |

Use Node 20.19 or newer (or 22.12+); check the current Vite release notes if the scaffold complains.

```bash
# 1. scaffold (from the repository root)
npm create vite@latest frontend -- --template react-ts
cd frontend
npm install

# 2. runtime dependencies
npm install react-router @tanstack/react-query zustand zod react-hook-form @hookform/resolvers \
  better-auth clsx d3-force d3-zoom d3-selection \
  @radix-ui/react-select @radix-ui/react-dialog @radix-ui/react-checkbox \
  @radix-ui/react-radio-group @radix-ui/react-tooltip @radix-ui/react-popover lucide-react

# 3. styling
npm install tailwindcss @tailwindcss/vite

# 4. dev dependencies
npm install -D @types/node @types/d3-force @types/d3-zoom @types/d3-selection \
  @tanstack/react-query-devtools eslint-plugin-jsx-a11y prettier \
  vitest jsdom @testing-library/react @testing-library/user-event @testing-library/jest-dom \
  msw @playwright/test
npx playwright install chromium
```

Three config edits finish the setup:

1. In `vite.config.ts`, add the `@tailwindcss/vite` plugin and an alias so `@` points to `src`.
2. In `tsconfig.app.json`, set `"strict": true` and `"paths": { "@/*": ["./src/*"] }`.
3. Add `@import "tailwindcss";` at the top of `src/styles/index.css`, and import that file once in `main.tsx`.

The dev server runs at `http://localhost:5173`; proxy `/api` to `http://localhost:5000` in `vite.config.ts` so the browser never sees a cross-origin call.

## Architecture

The app has four layers, and a file may only import from the layers below it: `app/` wires, `screens/` render one screen each, `features/` hold code two or more screens share, and `ui/`, `api/`, `lib/` are the foundation.

&#91;embedded content: frontend layers · 4 levels, imports point down\]

Screens may also use `ui/` and `api/` directly. What they may not do is import another screen.

All pages share one HTML shell and navigate client-side, so the session and the unsaved plan draft survive moving between screens. Serving a separate HTML file per screen is the alternative; it would reload the app and reset that state on every navigation.

A protected screen loads in four steps:

1. The router matches the path and lazy-loads that screen's code chunk.
2. `RequireAuth` reads `useSession()`; with no session it redirects to `/login`.
3. `RequireOnboarded` reads the profile query; if setup is incomplete it redirects to `/onboarding/coursework`.
4. `AppShell` renders the header and dock, the screen mounts, runs its queries, and shows its own loading and error states.

## File tree

Code is grouped by screen first, then by shared feature, then by design-system primitive, and imports may only point downward through that order.

```text
frontend/
├─ index.html
├─ package.json
├─ vite.config.ts
├─ tsconfig.json  tsconfig.app.json  tsconfig.node.json
├─ eslint.config.js
├─ .env.example                  # VITE_API_URL, VITE_AUTH_URL
├─ e2e/                          # Playwright specs
│  ├─ onboarding.spec.ts
│  └─ plan-edit.spec.ts
└─ src/
   ├─ main.tsx                   # mounts <App />
   ├─ app/                       # wiring only, no screen logic
   │  ├─ App.tsx
   │  ├─ providers.tsx           # QueryClient, auth session, toasts
   │  ├─ router.tsx              # the route table, lazy screens
   │  ├─ layouts/
   │  │  ├─ PublicLayout.tsx     # login
   │  │  ├─ OnboardingLayout.tsx # brand row and step indicator
   │  │  └─ AppShell.tsx         # header, floating dock, search overlay slot
   │  └─ guards/
   │     ├─ RequireAuth.tsx
   │     └─ RequireOnboarded.tsx
   ├─ screens/                   # one folder per screen; never import each other
   │  ├─ login/
   │  │  ├─ LoginScreen.tsx
   │  │  └─ PlanSkyline.tsx
   │  ├─ onboarding/
   │  │  ├─ CourseworkScreen.tsx
   │  │  ├─ ProfileScreen.tsx
   │  │  ├─ BuildingPlanScreen.tsx
   │  │  ├─ components/          # ImportChoice, ApasUploader, ManualEntry
   │  │  └─ onboarding.store.ts  # survives Back; cleared on Finish
   │  ├─ dashboard/
   │  │  ├─ DashboardScreen.tsx
   │  │  ├─ components/          # MetricCard, PercentRing, CourseList, UserDetails, BuildPlannerButton
   │  │  └─ useDashboard.ts
   │  ├─ flow-chart/
   │  │  ├─ FlowChartScreen.tsx
   │  │  ├─ components/          # SemesterCard, CurrentClassesCard, GraduationCard, CourseOptionRow, BuildingCard, GraphCanvas
   │  │  └─ graph/               # buildGraph, forceLayout, drawGraph, hitTest, useForceGraph
   │  ├─ course-catalog/
   │  │  ├─ CatalogScreen.tsx
   │  │  ├─ components/          # FilterBar, FilterSheet, ResultsList, ResultsSkeleton
   │  │  └─ useCatalogSearch.ts
   │  └─ settings/
   │     ├─ SettingsScreen.tsx
   │     ├─ components/          # ProfileSection, GoalsSection, PlanningSection, SaveBar
   │     └─ settings.schema.ts   # Zod schema for the form
   ├─ features/                  # used by two or more screens
   │  ├─ course-detail/          # CourseDrawer, PrereqList, ProfessorLinks
   │  ├─ plan/                   # plan.store (draft edits), usePlan, planRules (eligibility), UnsavedPlanBar
   │  ├─ search/                 # SearchOverlay
   │  └─ auth/                   # auth.client, useSession
   ├─ ui/                        # design system; no business logic, no API calls
   │  ├─ Button  IconButton  TextField  TextArea  Select  Combobox
   │  ├─ Checkbox  RadioGroup  SegmentedControl  Stepper  Dropzone
   │  ├─ Badge  StatusBadge  Chip  Callout  Card
   │  ├─ Drawer  BottomSheet  Dialog  Tooltip  Toast
   │  ├─ ProgressBar  ProgressRing  Skeleton  EmptyState  Icon
   │  └─ index.ts
   ├─ api/
   │  ├─ client.ts               # fetch wrapper, error mapping
   │  ├─ endpoints/              # courses, plan, profile, transcripts
   │  ├─ queryKeys.ts
   │  └─ schemas.ts              # Zod schemas and inferred types
   ├─ hooks/                     # useMediaQuery, useReducedMotion, useFocusTrap
   ├─ lib/                       # cn, format, terms
   ├─ styles/
   │  ├─ index.css               # Tailwind import, base rules
   │  └─ tokens.css              # color, space, radius, type variables
   └─ test/                      # setup.ts, MSW handlers, fixtures
```

The import rule is enforced, not agreed on: `eslint.config.js` uses `no-restricted-imports` so a file under `screens/dashboard/` cannot import from `screens/flow-chart/`, and nothing under `ui/` can import from `features/`, `screens/`, or `api/`. When two screens need the same code, it moves to `features/`.

## Screen map

There are eight routes plus a not-found route, and each loads its own code chunk the first time it is visited.

| Route | Screen module | Guard | Data (endpoints proposed in the API section) | States to build |
| --- | --- | --- | --- | --- |
| `/login` | `screens/login` | Redirects away if already signed in | None | Default, signing in, rejected non-UMN account |
| `/onboarding/coursework` | `screens/onboarding` | `RequireAuth` | `POST /transcripts` | Idle, uploading, parsing, parsed, unreadable scan, manual entry, skipped |
| `/onboarding/profile` | `screens/onboarding` | `RequireAuth` | `PUT /profile` | Validation errors, saving |
| `/onboarding/building` | `screens/onboarding` | `RequireAuth` | `POST /plans/generate` | Generating, ready, failed with retry |
| `/dashboard` | `screens/dashboard` | `RequireAuth`, `RequireOnboarded` | `GET /summary`, `GET /plan` | Loading skeleton, empty plan, missing metric shown as N/A, error. Includes the Build my planner button |
| `/flow-chart` | `screens/flow-chart` | `RequireAuth`, `RequireOnboarded` | `GET /plan`, `GET /programs/:id/graph` | Loading, planner building, semester cards, over credit load, locked course, unsaved edits |
| `/catalog` | `screens/course-catalog` | `RequireAuth`, `RequireOnboarded` | `GET /courses` with query and filters | Initial, loading, results, no results, error |
| `/settings` | `screens/settings` | `RequireAuth`, `RequireOnboarded` | `GET /profile`, `PUT /profile` | Saved, unsaved, saving, could not save, validation error |
| `*` | `app/router.tsx` | None | None | Link back to dashboard |

Three decisions keep the screens independent:

1. **Course details are a search parameter, not a route.** Opening a course sets `?course=CSCI 2041` on the current screen, so the drawer is linkable, Back closes it, and no screen needs to know about another screen's detail page.
2. **Onboarding is three routes, not one component with a step counter.** Back and Forward work in the browser, and a refresh resumes the same step. Entered coursework lives in `onboarding.store.ts`, so going back never discards it.
3. **The dock and header live in `AppShell` only.** Login and onboarding use their own layouts, so those screens carry no app navigation.

## Design system

Surfaces are solid ivory and warm white with a 1px border, `backdrop-filter` is removed everywhere, and screens build only from our own `ui/` components.

### Tokens

All tokens are CSS variables in `styles/tokens.css`, exposed to Tailwind through its theme, so a color changes in one place.

| Token | Value | Use |
| --- | --- | --- |
| `--surface-page` | `#E6E0D2` | Flat page background; no gradients, orbs, or grain |
| `--surface-card` | `#FBF8F2` | Cards, panels, table containers |
| `--surface-raised` | `#FFFFFF` | Dock, drawer, bottom sheet, menus |
| `--border` | `rgba(32, 26, 27, 0.14)` | Card and field outlines |
| `--maroon` / `--gold` | `#7A0019` / `#FFCC33` | Primary action and active state / progress and selection accents |
| `--ink` / `--muted` | `#201A1B` / `#625A5C` | Text and secondary text |
| `--shadow-card` | `0 1px 2px rgba(32, 26, 27, 0.06)` | Resting cards |
| `--shadow-raised` | `0 12px 30px rgba(32, 26, 27, 0.14)` | Dock, drawer, sheet |

Success, warning, and danger keep the values in the design doc (`#237A57`, `#A86400`, `#B42318`). Radius is 8px or less, spacing is a 4px scale, titles use Young Serif, interface text uses Hanken Grotesk, and numbers use tabular figures. The percent-complete card stays solid maroon with a gold ring.

### Custom elements instead of native widgets

Every interactive control comes from `src/ui/`. Radix supplies behavior and accessibility; we supply all markup and styling, so nothing shows a browser-default widget.

| Native element | Our component | Built on |
| --- | --- | --- |
| `<select>` | `Select` | Radix Select |
| `<datalist>` | `Combobox` | Radix Popover and a filtered listbox |
| `<input type="checkbox">` | `Checkbox` | Radix Checkbox |
| `<input type="radio">` | `RadioGroup`, `SegmentedControl`, `OptionCard` | Radix Radio Group |
| `<input type="number">` and `range` | `Stepper` | Two `IconButton`s and a live value |
| `<input type="file">` | `Dropzone` | Hidden input inside our drop area and button |
| `<progress>` | `ProgressBar`, `ProgressRing` | `role="progressbar"` with text label |
| `<dialog>` and `title` tooltips | `Dialog`, `Drawer`, `BottomSheet`, `Tooltip` | Radix Dialog and Tooltip |
| `<button>` | `Button`, `IconButton` | Typed `variant` and `size` props |

Text fields (`TextField`, `TextArea`) still render a real `<input>` or `<textarea>` underneath with our styling. Replacing the editable element itself breaks mobile keyboards, autofill, and input methods, so only its appearance is custom.

Two checks keep this honest. `no-restricted-syntax` forbids `<select>`, `<textarea>`, and `<input>` in any file outside `src/ui/`. Each `ui/` component has a Testing Library test for keyboard use and its accessible name.

Icons come from lucide-react, imported by name (for example `import { Search } from "lucide-react"`) and wrapped by `ui/Icon`, which sets the size and `aria-hidden`. An icon-only button always gets an accessible name.

## Flow chart: semester cards and graph

The flow chart screen opens on semester cards, because a card list can be read by a screen reader, tabbed through, and used on a phone, which a canvas cannot guarantee. The graph is a second view of the same plan data.

- **Current classes card:** the Fall 2026 courses with credits and an In progress status.
- **One card per semester to graduation:** each shows planned credits against the preferred load with a text progress bar (for example, 11 of 15 credits), the planned courses with a Remove button, and a Courses you could take list with an Add button.
- **Only eligible courses are offered:** a course appears for a semester when its prerequisites are finished, in progress, or planned in an earlier semester, and it is offered in that season.
- **Locked courses** stay in their card with the reason in words, such as a major restriction.
- **Graduation card:** projected credits against 120, with a plain-language note when the plan falls short.
- **Accessibility:** each card is a section with a heading, Add and Remove buttons name the course and semester, a live region announces every change, and credit and status never rely on color alone.

The dashboard's Build my planner button starts plan generation from the user's current progress, credit load, and graduation target, then opens this screen with the new cards as an unsaved draft. The user reviews, edits, and saves or discards.

### Graph view

The graph is a force-directed network drawn on a canvas, like Obsidian's graph view: courses are dots, prerequisites are thin lines, and the layout settles by itself.

We write this ourselves with `d3-force` (layout), `d3-zoom` (pan and pinch), and Canvas 2D (drawing). A wrapper library would save a day now but would fight us on status shapes, term ordering, and the list-view twin.

**What it looks like**

- **Nodes:** small circles sized by credits. Status is a shape plus a color: completed is a solid dot, in progress is a ring with a center dot, planned is a hollow maroon ring, available is a thin gray ring, locked is a diamond.
- **Edges:** 1px lines with no arrowheads, as in Obsidian. Arrowheads appear only on lines of the selected course.
- **Labels:** course code beside each dot. The selected course also shows its title and status in words.
- **Term order:** a weak horizontal force pulls earlier terms left and later terms right, so the graph reads as a plan while still looking organic.

**How it behaves**

| Input | Result |
| --- | --- |
| Hover a node | Its prerequisites and dependents stay bright; everything else fades to about 15% |
| Click a node | Sets `?course=CODE`, which opens the course drawer and holds the highlight |
| Drag a node | Pins it where dropped; the rest of the graph reflows around it |
| Scroll, pinch, or drag the background | Zoom and pan |
| Fit button or double-click background | Frames the whole plan |
| Reset view | Clears pins, selection, and zoom, then reheats the layout |

**Core of the layout**, in `graph/forceLayout.ts`:

```ts
import { forceSimulation, forceLink, forceManyBody, forceCollide, forceX, forceCenter } from "d3-force";

export function createLayout(
  nodes: GraphNode[],
  links: GraphLink[],
  termX: (term: TermId | null) => number,
) {
  return forceSimulation(nodes)
    .force("link", forceLink<GraphNode, GraphLink>(links).id((d) => d.id).distance(72).strength(0.6))
    .force("charge", forceManyBody().strength(-140))
    .force("collide", forceCollide<GraphNode>((d) => nodeRadius(d) + 6))
    .force("term", forceX<GraphNode>((d) => termX(d.term)).strength(0.08))
    .force("center", forceCenter(0, 0))
    .alphaDecay(0.04);
}
```

**Implementation notes**

- `buildGraph.ts` is a pure function from the plan and the program graph to nodes and links, so it is unit-tested without a browser.
- `drawGraph.ts` is a pure draw function over a canvas context and state, scaled by `devicePixelRatio`. The draw loop runs only while the simulation is hot or the user is interacting.
- Hit-testing converts the pointer through the inverse zoom transform and calls the simulation's `find`. The `d3-zoom` filter ignores pointer-down on a node, and our own pointer handlers drag the node, so `d3-drag` is not needed.
- The last layout is cached per program in memory, so returning to the screen does not re-explode the graph.
- With reduced motion on, the layout is advanced to rest before the first paint instead of animating.
- **Accessibility:** the canvas has `role="img"` and a label with course and link counts. The Semesters view is the full accessible equivalent and is the default on every screen size. Keyboard navigation inside the canvas is deferred (see open questions).

## State, data fetching, and API contract

Server data lives in TanStack Query, in-progress edits live in small Zustand stores, and every response is parsed with a Zod schema before any component sees it.

- **Plan edits are a draft.** `features/plan/plan.store.ts` holds only the changes made since the last save. The flow chart and catalog both read "saved plan plus draft". Save sends `PUT /plan` and invalidates the `plan` query; Discard clears the draft. A router blocker warns before leaving a screen with unsaved edits.
- **Settings use React Hook Form with a Zod schema.** Its `isDirty`, `isSubmitting`, and error state drive the Saved, Unsaved, Saving, and Could not save indicator, and the save bar.
- **Transcript parsing is polled.** After upload, the screen polls `GET /transcripts/:id` every second while status is `parsing`. A `no_text` status shows the scanned-PDF recovery step (OCR or manual entry) instead of a silent failure.
- **Errors are mapped once.** `api/client.ts` turns failures into an `ApiError` with a code. Each screen wraps its content in an error boundary with a Retry button.
- **Auth** comes from the Better Auth client. `useSession()` feeds `RequireAuth`, and `RequireOnboarded` checks the profile query.

The endpoints below are proposed from what each screen needs; confirm names and shapes with the backend before building the matching Zod schema. Flask publishes no schema of its own, so the Zod schemas in api/schemas.ts are the only written contract; have the backend owner review them.

| Method and path | Used by | Returns or accepts |
| --- | --- | --- |
| `GET /api/v1/summary` | Dashboard | GPA, credits completed and total, percent complete |
| `GET /api/v1/plan` | Dashboard, Flow chart | Terms, each with courses and status |
| `PUT /api/v1/plan` | Flow chart | Saved draft: list of course and term changes |
| `POST /api/v1/plans/generate` | Onboarding | Starts plan generation; returns a job id |
| `GET /api/v1/programs/:id/graph` | Flow chart | Course nodes and prerequisite edges for the major |
| `GET /api/v1/courses` | Catalog, search overlay | Paged results; query, subject, level, credits, term, requirement, availability |
| `GET /api/v1/courses/:code` | Course drawer | Prerequisites, concurrent requirements, offered terms, professors, link targets |
| `GET /api/v1/profile`, `PUT /api/v1/profile` | Settings, Onboarding | Name, major, standing, career goals, credit load, graduation target |
| `POST /api/v1/transcripts` | Onboarding | Multipart PDF; returns a transcript id |
| `GET /api/v1/transcripts/:id` | Onboarding | Status: `parsing`, `parsed`, `no_text`, or `failed`, plus parsed courses |
| `POST /api/v1/transcripts/:id/ocr` | Onboarding | Retries parsing with text recognition |

## Accessibility, testing, build and deploy

Accessibility is built into the `ui/` components once, so screens inherit it, and the build ships as static files behind the same VPS and Cloudflare setup the README describes.

- **Accessibility rules in code.** Every touch target uses a `--hit: 44px` minimum. `StatusBadge` always renders an icon and a text label, never color alone. `Drawer`, `BottomSheet`, and `Dialog` trap focus and return it on close. `eslint-plugin-jsx-a11y` runs in lint. `useReducedMotion()` makes the graph settle instantly instead of animating.
- **Unit tests (Vitest)** cover the logic that can silently be wrong: `planRules.ts` prerequisite and restriction checks, `buildGraph.ts`, and term math in `lib/terms.ts`.
- **Component tests (Testing Library)** cover each `ui/` primitive for keyboard use and accessible name.
- **Screen tests** render a screen with MSW handlers and check its loading, empty, error, and success states.
- **End-to-end tests (Playwright)** run three flows: sign in through onboarding to the dashboard, add a course and save the draft, and upload a scanned PDF and recover through manual entry.

Scripts in `package.json`: `dev`, `build`, `preview`, `typecheck` (`tsc -b`), `lint`, `test`, and `e2e`.

Deploy: `npm run build` writes static files to `dist/`. The web server must serve `index.html` for any unknown path (for example `try_files $uri /index.html;` in nginx), because routes such as `/flow-chart` are real browser paths. `/api` is reverse-proxied to the Flask API. Cloudflare sits in front for DNS and proxying. Environment values use the `VITE_` prefix and are public, so no secret ever goes in the frontend.

## Build order and open questions

Build the shell and every route as stubs first, then fill screens from simplest to riskiest, ending with the flow chart because it depends on plan data and the draft store.

1. **Scaffold:** Vite project, tokens, path alias, ESLint boundary and no-native-widget rules.
2. **`ui/` primitives:** Button, TextField, Select, Checkbox, RadioGroup, Badge, Card, Drawer, BottomSheet.
3. **App shell:** router, layouts, guards, and a stub for each of the eight routes, so navigation works from day one.
4. **API layer:** client, Zod schemas, MSW handlers, query keys.
5. **Login and onboarding:** onboarding store, uploader states including the unreadable-scan recovery.
6. **Dashboard:** metric cards, percent ring, class lists.
7. **Catalog and course drawer:** search, filters, results states, `?course=` drawer.
8. **Settings:** form schema, save states, save bar.
9. **Flow chart:** semester cards, draft plan, unsaved bar, then the graph view.
10. **Hardening:** Playwright flows, accessibility pass, bundle check.

**Open questions**

- [ ] Better Auth is a TypeScript server library but the backend is Flask: run it as a small Node service, or do Google OAuth inside Flask and drop Better Auth?
- [ ] Confirm the proposed endpoint names and response shapes with whoever owns the backend.
- [ ] Should arrow-key navigation inside the graph canvas ship in v1, or is the Semesters view enough for now?
- [ ] How many courses does a major's program graph hold? Above roughly 500 nodes, Canvas 2D should be revisited.
- [ ] Does the Social Coding team want Radix as a dependency, or hand-built primitives with no library?
