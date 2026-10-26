# Gopher Planner Feature Audit

**Audit date:** 2026-10-26
**Repository:** Gopher Planner
**Revision audited:** `0e81d38` on `main`
**Scope:** `frontend/` and `backend/`, checked against `README.md`, `docs/design-rules.md`, and `docs/Gopher Planner Frontend Technical Design.md`

## How to read this document

| Status | Meaning |
| --- | --- |
| Complete | Works end to end and matches the documented behavior closely enough for normal use. |
| Partial | A usable slice exists, but important behavior, data, or states are absent. |
| Mock only | The UI behaves as if the feature works, but data is seeded, in-memory, or simulated. |
| Missing | No implementation exists in that layer. |
| Not started | Neither layer contains the feature. |

This audit covers functional completeness. It does not score visual polish except where missing states or controls block a documented feature.

## Method and limitations

- Reviewed the frontend and backend source, route registration, migrations, package manifests, design documents, and the catalog SQLite database.
- Verified catalog counts directly against `backend/data/courses.db`.
- Did not run the Google OAuth flow, a live upload, or browser-based end-to-end tests. Findings are based on code and data inspection, so runtime issues outside that evidence may still exist.

## Executive summary

The foundation is real: Google sign-in, sessions, profile read and update, the app shell, responsive layouts, catalog browsing, catalog search, and course detail for catalog data all work against the Flask API.

The core product is not complete. The four-year planner is still a demo:

1. Transcript and manual coursework are simulated and never persisted.
2. Plan generation is a 200 ms mock that returns `mock-job`.
3. There is no backend plan model or plan API.
4. Dashboard summary and plan data come from `src/api/mock/seed.json`.
5. A newly onboarded user sees the same seeded plan regardless of their coursework.
6. Catalog courses that are not already in the seeded plan cannot be added, even though the UI shows an Add button.
7. Degree requirements, prerequisite validation, concurrent-enrollment checks, professors, Rate My Professors, and course-specific Gopher Grades are absent.
8. There are no frontend or backend tests.

Two smaller issues can break a local setup or a new contributor: `frontend/.env.example` documents an API URL that produces the wrong auth path, and the root `README.md` describes a FastAPI and Better Auth stack that the repository does not use.

## Status at a glance

| Feature | Frontend | Backend | Overall |
| --- | --- | --- | --- |
| Google sign-in and sessions | Complete | Complete | Complete |
| Profile read and update | Complete | Complete | Complete |
| App shell, routing, responsive layout | Complete | Not applicable | Complete |
| Course catalog browse and search | Partial | Partial | Partial |
| Course detail drawer | Partial | Partial | Partial |
| Transcript upload and parsing | Mock only | Missing | Not started |
| Manual coursework entry | Partial | Missing | Not started |
| Four-year plan generation | Mock only | Missing | Not started |
| Plan persistence and saved plans | Mock only | Missing | Not started |
| Dashboard summary and progress | Partial | Missing | Not started |
| Flow chart and semester editing | Partial | Missing | Partial |
| Degree requirements | Partial | Missing | Not started |
| Prerequisite and concurrent validation | Partial | Partial | Not started |
| Professor data and Rate My Professors | Missing | Missing | Not started |
| Gopher Grades | Stub | Missing | Not started |
| Settings | Partial | Complete | Partial |
| Catalog seed data and programs | Not applicable | Partial | Partial |
| Caching | Not applicable | Missing | Missing |
| Automated tests and linting | Missing | Missing | Missing |

## 1. Authentication and profile

### What works

- Google credential exchange, UMN email enforcement, verified-email enforcement, opaque session cookies, expiry, revocation, and logout exist in `backend/app/api/v1/auth.py` and `backend/app/core/google_auth.py`.
- `GET /api/v1/profile` and `PUT /api/v1/profile` are implemented in `backend/app/api/v1/profile.py:67` and `:83`.
- The frontend restores sessions and protects authenticated routes with `frontend/src/features/auth/session.store.ts` and `frontend/src/app/guards/RequireAuth.tsx`.
- Onboarding profile and Settings both write through the real profile endpoint.

### Gaps to finish

- **API base URL bug.** `frontend/.env.example:2` sets `VITE_API_URL=http://localhost:5000`. The auth client appends `/auth/google`, producing `http://localhost:5000/auth/google`, while the backend route is `/api/v1/auth/google` (`frontend/src/features/auth/google.ts:12-14`, `:37`; `backend/app/api/v1/auth.py:16`). Either remove `VITE_API_URL` for local development or document `http://localhost:5000/api/v1`.
- The sign-in button renders an empty container if the Google client ID or Google script is unavailable (`frontend/src/features/auth/GoogleSignInButton.tsx:23-28`, `:53-61`). It needs a visible configuration error and retry.
- Terms and Privacy links point to `#terms` and `#privacy` with no targets (`frontend/src/screens/login/LoginScreen.tsx:93-103`).
- The backend requires `JWT_SECRET` but never uses it, and `pyjwt` is an unused dependency (`backend/app/core/config.py:30`, `backend/pyproject.toml:14`). Remove both or use the secret for the intended token strategy.
- The backend user ID is an integer (`backend/app/api/v1/auth.py:69`), while the frontend types it as a string (`frontend/src/features/auth/session.store.ts:5`). Align the contract before adding more auth consumers.
- Google refreshes `user.name` on every login (`backend/app/api/v1/auth.py:167-170`), so a name edited in Settings is overwritten at the next sign-in.
- Major, standing, and graduation target are free strings on the backend. Add validation against the program options once those options come from the API.
- There is no rate limiting, expired-session cleanup, or sign-out-all-devices behavior.

### Done when

- A documented local env file signs in successfully without path edits.
- Missing Google configuration produces a visible error.
- Auth and profile have backend tests for non-UMN rejection, expired sessions, invalid origin, and profile validation.

## 2. Onboarding: transcript upload, parsing, and manual entry

This is the largest missing user flow. The UI exists, but no real coursework reaches the database.

### What works

- Onboarding screens, method selection, PDF drag and drop, manual course search, step indicator, and profile step are implemented.
- Manual course entry uses the real catalog search API.
- The upload UI has readable, scanned, and manual-entry recovery surfaces.

### What is missing

- **No backend transcript feature.** There is no route, model, migration, service, parser, or file storage. `backend/app/parsers/` contains only `README.md`, and `pdfplumber` is not a dependency.
- `POST /api/v1/transcripts`, `GET /api/v1/transcripts/:id`, and `POST /api/v1/transcripts/:id/ocr` from the design contract do not exist.
- `uploadTranscript()` is an in-memory `Map` with a timer (`frontend/src/api/endpoints.ts:176-207`).
- Upload progress is simulated at 14 percent every 120 ms (`frontend/src/screens/onboarding/components/ApasUploader.tsx:26-32`).
- The `failed` transcript status has no UI. It falls through to the spinner and reading message (`ApasUploader.tsx:66-78`, `:112`).
- `uploadTranscript()` rejection is not caught in `start()` (`ApasUploader.tsx:34-47`).
- There is no parsed-course review or correction step. A parse only reports counts (`ApasUploader.tsx:85-89`).
- Manual entries live in a memory-only Zustand store and are discarded (`frontend/src/screens/onboarding/onboarding.store.ts:27-52`, `frontend/src/screens/onboarding/BuildingPlanScreen.tsx:38`).
- `Skip for now` records no state and triggers no different behavior (`frontend/src/screens/onboarding/CourseworkScreen.tsx:49-55`).
- Onboarding is not resumable after refresh, contrary to `docs/design-rules.md:279`.
- The parent screen disables its transcript query and relies on the child populating the same cache key (`CourseworkScreen.tsx:18-21`). Replace this with a parent-owned transcript query.

### Done when

- A PDF can be uploaded, parsed, reviewed, corrected, and persisted.
- A scanned PDF reaches `no_text`, then OCR or manual entry, then a persisted result.
- Manual courses persist as completed or in-progress records.
- Refresh during onboarding does not lose uploaded or entered coursework.
- The generation request can read the persisted coursework.

## 3. Four-year plan generation

### Current behavior

`generatePlan()` waits and returns `{ jobId: "mock-job" }` (`frontend/src/api/endpoints.ts:102-106`). `BuildingPlanScreen` runs artificial timers, calls `updateProfile({ onboarded: true })`, then clears the onboarding store (`frontend/src/screens/onboarding/BuildingPlanScreen.tsx:21-52`).

No generated plan is produced. The dashboard later reads the seeded mock plan.

The flow-chart Build action is also local, running a greedy client-side algorithm (`frontend/src/features/plan/usePlan.ts:68-70`, `frontend/src/features/plan/planRules.ts`).

### What is missing

- No `POST /api/v1/plans/generate` route.
- No generation service, job status, or persisted result.
- No use of completed coursework, current courses, or transfer credit in generation.
- No validation of prerequisites, concurrent requirements, offered terms, restrictions, or graduation target during generation.
- No handling of course-load preferences beyond the local greedy algorithm.
- No server-side plan ownership.

### Done when

- Generation accepts profile and coursework inputs.
- The generated plan is stored and returned to the dashboard and flow chart.
- Completed and in-progress courses are excluded from future placement.
- Preferred credit load, graduation target, prerequisites, concurrent rules, and offered terms are respected.
- The UI has a real waiting, success, and failure path with retry.

## 4. Plan persistence and saved plans

### What works

- The frontend has a solid draft model: saved plan plus unsaved changes, an unsaved bar, discard, and optimistic save behavior (`frontend/src/features/plan/usePlan.ts`, `frontend/src/features/plan/plan.store.ts`).

### What is missing

- No `plans`, `plan_terms`, or `plan_courses` models.
- No `GET /api/v1/plan` or `PUT /api/v1/plan`.
- No `plans/generate` job model or migration.
- `savePlan()` only mutates courses that already exist in the seeded plan. It cannot create a plan course (`frontend/src/api/endpoints.ts:91-100`).
- Plan data persists to browser `localStorage` through the mock database, not to PostgreSQL.
- There is no route or UI for multiple saved plans, plan names, create, duplicate, rename, load, or delete.
- There is no server-side ownership check because there is no server-side plan.
- There is no unsaved-change navigation blocker. The draft bar only renders on plan-edit screens (`frontend/src/app/layouts/AppShell.tsx:184`).
- There is no conflict handling for stale plan data across tabs or devices.

### Done when

- Plans are stored per user and protected at the route and service boundaries.
- A plan can be created, loaded, edited, saved, and deleted.
- A course can be added from the catalog, not only edited if already present.
- Unsaved edits warn before navigation and survive a refresh as a draft or are explicitly discarded.

## 5. Dashboard and summary

### What works

- The dashboard layout, metric cards, current classes, future classes, user details, and next-semester link exist (`frontend/src/screens/dashboard/DashboardScreen.tsx`).

### What is missing

- `GET /api/v1/summary` does not exist.
- `getSummary()` reads seeded data (`frontend/src/api/endpoints.ts:19-23`).
- GPA, credits, completion percentage, program, and source are not derived from transcript or plan data.
- Summary failures are ignored by `usePlan()`; only plan and profile errors are surfaced (`frontend/src/features/plan/usePlan.ts:54-61`).
- Metric cards render empty values while loading instead of `N/A` (`DashboardScreen.tsx:42`, `:55-67`). The design requires a nonblank missing-value state (`docs/design-rules.md:184`).
- `Build my planner` navigates to the local greedy Build action, not server generation (`DashboardScreen.tsx:39`).
- The total-credit fallback is 120 when no summary exists (`usePlan.ts:54`).

### Done when

- Summary values come from the backend and update after plan or coursework changes.
- Loading, empty, and error states are distinct and visible.
- Dashboard data changes when the student's plan changes.

## 6. Flow chart and semester editing

### What works

- Semester cards show current, future, planned, and locked courses with Add and Remove actions.
- The graph view renders nodes and links, supports hover, selection, pinning, background pan, wheel zoom, fit, and reset.
- The semester view is a usable accessible alternative to the graph.

### What is missing

- Plan data is still mocked, so the graph does not represent the student's real plan.
- `POST /api/v1/plans/generate` is not called from the Build action.
- `GET /api/v1/programs/:id/graph` is not implemented, so graph edges come only from the current mock plan and local logic.
- The major selector updates state that is never consumed (`frontend/src/screens/flow-chart/FlowChartScreen.tsx:32`, `:171-177`).
- There is no academic-year or term filter, despite the toolbar requirement at `docs/design-rules.md:194`.
- The graph hint says pinch to zoom, but only wheel and single-pointer events are handled (`FlowChartScreen.tsx:227`, `frontend/src/screens/flow-chart/components/GraphCanvas.tsx:243-249`).
- The graph canvas has no keyboard navigation (`GraphCanvas.tsx:264-270`). The design defers keyboard support, but it is still a completion item.
- There is no unsaved-change blocker when leaving the screen.
- Elective alternatives are capped at four with no show-more control (`frontend/src/screens/flow-chart/components/SemesterView.tsx:65`).
- Prerequisite conflicts are not shown before a course is moved or added.

### Done when

- The chart renders the real saved plan and program graph.
- Build runs server generation.
- Term filtering works.
- Unsaved edits are protected.
- Prerequisite and concurrent conflicts appear before save.

## 7. Course catalog

### What works

- Real `GET /api/v1/courses` search, server pagination, filters for subject, level, credits, term, and availability, active-filter chips, loading skeletons, empty state, error state, and retry.
- Global search uses the real catalog API.

### What is missing

- **Add to plan is broken for catalog-only courses.** Results show an Add button for any available course (`frontend/src/screens/course-catalog/components/ResultsList.tsx:45`, `:84-91`), but `onAdd` refuses when the course is not already in the seeded plan (`frontend/src/screens/course-catalog/CatalogScreen.tsx:108-123`). The drawer also has no add action for catalog-only courses (`frontend/src/features/course-detail/CourseDrawer.tsx:110-116`).
- The requirement filter is absent from `FilterFields`, the empty filter state, and the query builder, even though the type and backend support it (`frontend/src/screens/course-catalog/components/FilterFields.tsx:3-40`, `frontend/src/api/endpoints.ts:112-130`).
- Subject options are hardcoded to CSCI and MATH (`FilterFields.tsx:18`), and the API already exposes catalog subjects.
- Availability always assumes Spring because the frontend never sends `nextTerm` (`frontend/src/api/endpoints.ts:127-129`, `backend/app/api/v1/courses.py:96`).
- Search fires on every keystroke without debounce (`frontend/src/screens/course-catalog/CatalogScreen.tsx:186-191`).
- There is no course comparison feature, despite the catalog purpose in `docs/design-rules.md:226`.
- Catalog failures return HTTP 500 on the backend, while the frontend only maps 503 to the catalog-unavailable message (`backend/app/api/v1/courses.py:208-210`, `:249-251`; `frontend/src/api/endpoints.ts:146`, `:167`).

### Done when

- Any catalog course can be added to the plan.
- All documented filters work, including requirement.
- Filter options come from the API.
- Error codes and messages match the backend contract.
- The catalog covers more than two subjects.

## 8. Course detail drawer

### What works

- Real catalog detail loading, retry, credits, offered terms, grading basis, repeatability, description, prerequisite trees, and original prerequisite text.

### What is missing

- No historical professors.
- No Rate My Professors links.
- No concurrent-requirement display.
- No course-specific Gopher Grades link. Every course links to `https://umn.lol` (`frontend/src/features/course-detail/CourseDrawer.tsx:250-260`).
- `resolvedPrerequisites` is returned by the backend and typed in the frontend, but never rendered (`backend/app/api/v1/courses.py:243-246`, `frontend/src/api/types.ts:72-75`).
- The catalog detail contract has no professor, concurrent, RMP, or grades fields (`docs/Gopher Planner Frontend Technical Design.md:316`).
- No add-to-plan action when the course is not already in the plan.

### Done when

- Detail shows professors, concurrent requirements, RMP when available, and a course-specific grade link.
- Missing external data degrades gracefully instead of disappearing.
- A catalog-only course can be added from the drawer.

## 9. Degree requirements and prerequisite validation

### What works

- The catalog stores structured prerequisite JSON, prerequisite source text, unresolved codes, and 357 prerequisite edges.
- The drawer renders prerequisite trees.
- The frontend has requirement labels for Major core, Math and stats, Elective, and Liberal ed.

### What is missing

- No programs table, requirement table, requirement expression model, or progress calculation.
- No `requirements` route despite the placeholder in `backend/app/api/v1/README.md`.
- No `GET /api/v1/programs/:id/graph`.
- No mapping from raw catalog requirement codes such as `001186` to user-facing requirement categories.
- No prerequisite evaluation service. Nothing checks whether a student has completed, is taking, or plans a prerequisite earlier.
- No concurrent-enrollment field or evaluation. Concurrent rules exist mostly as free text.
- No validation of non-course restrictions such as college, major, honors, placement, or instructor consent.
- Prerequisite codes are sometimes missing subjects or use inconsistent casing, so resolution is unreliable.
- 188 of 324 catalog courses have no requirement value (`requirements = "-"`).
- No tests cover prerequisite trees, concurrent rules, or requirement progress.

### Done when

- Programs and their requirements are stored and returned by the API.
- Requirement progress is computed from completed, in-progress, and planned courses.
- Prerequisite and concurrent rules are evaluated before a course is placed.
- User-facing requirement categories replace raw catalog codes.
- The flow chart and dashboard use the same requirement source of truth.

## 10. Professors, Rate My Professors, and Gopher Grades

### Status

- `backend/app/integrations/` contains only a README.
- There is no professor table, course-professor history, or endpoint. The plan type has a mock `professors` field, but the catalog contract has no professor data and nothing renders it.
- The mock plan type contains `professors` and `concurrent`, but neither is displayed.
- The header advertises professor search, but search only queries courses (`frontend/src/app/layouts/AppShell.tsx:126`, `frontend/src/features/search/useCourseSearch.ts:17-22`).
- Gopher Grades is a generic external link, not an integration.

### What is needed

- Historical professor data per course.
- A course-professor API or embedded detail fields.
- RMP lookup and link generation with availability handling.
- A course-specific Gopher Grades URL or imported grade data.
- UI in both the drawer and the plan course detail panel.

### Done when

- A planned or catalog course shows likely professors.
- RMP opens the matching professor when data exists.
- Gopher Grades opens the matching course when data exists.
- The UI clearly distinguishes unavailable data from an error.

## 11. Settings

### What works

- Real profile read and update.
- Grouped fields, save and discard, unsaved bar, and name validation.

### What is missing

- No Saving state. Only saved, unsaved, and error exist (`frontend/src/screens/settings/SettingsScreen.tsx:87-88`, `:112-116`), despite the design requirement at `docs/design-rules.md:269`.
- The preview checkbox for a failed save writes `mockFlags.failNextSettingsSave`, but nothing reads it (`SettingsScreen.tsx:101`, `frontend/src/api/mock/mockDb.ts:48`).
- Reset demo data clears local state and signs out, but it does not reset the backend profile or onboarding flag (`SettingsScreen.tsx:206-215`).
- Profile loading shows only the page title.
- Only the name is validated on submit. Major, standing, credit load, and graduation target are not validated.
- Options still come from mock data (`frontend/src/api/endpoints.ts:79-83`).
- The backend allows 1 to 30 credits while the UI enforces 12 to 25 (`backend/app/api/v1/profile.py:57`, `frontend/src/features/profile/profileRules.tsx:4-5`).

### Done when

- All four save states are real.
- Options come from the backend.
- Reset demo data either resets server state or is renamed to describe what it actually clears.
- Validation is consistent across the client and server.

## 12. Catalog data, programs, and caching

### Current catalog contents

Verified against `backend/data/courses.db`:

- 324 courses total.
- Every course is CSCI (138) or MATH (186).
- 188 courses have no requirement value.
- 357 prerequisite edges.
- Tables: `catalog`, `courses`, `prerequisite_edges`.
- Catalog version is `unknown`.

### Gaps

- No programs or degree-requirement data.
- No professors or teaching history.
- No course sections, meeting times, or real current-term availability.
- No seed or import scripts. `backend/scripts/` contains only a README.
- The catalog path is hardcoded (`backend/app/api/v1/courses.py:14`). `CATALOG_DATABASE_URL` in the README is ignored.
- No in-memory cache despite the documented caching decision. Every search opens a new SQLite connection.
- Alternating-year offerings are discarded by `parse_offered()` (`courses.py:48-50`).

### Done when

- Catalog and program data can be regenerated from a documented script.
- The catalog covers the majors the product claims to support.
- Requirement codes and program requirements are mapped.
- Professor history is available.
- Catalog lookups are cached with clear invalidation rules.

## 13. API contract and error handling

### Missing endpoints expected by the frontend or design

| Endpoint | Consumers | Backend |
| --- | --- | --- |
| `GET /api/v1/summary` | Dashboard | Missing |
| `GET /api/v1/plan` | Dashboard, flow chart | Missing |
| `PUT /api/v1/plan` | Flow chart | Missing |
| `POST /api/v1/plans/generate` | Onboarding | Missing |
| `GET /api/v1/programs/:id/graph` | Flow chart | Missing |
| `POST /api/v1/transcripts` | Onboarding | Missing |
| `GET /api/v1/transcripts/:id` | Onboarding | Missing |
| `POST /api/v1/transcripts/:id/ocr` | Onboarding | Missing |
| `GET /api/v1/options` or program options | Onboarding, Settings | Missing |
| Professor and grade data in course detail | Course drawer | Missing |

### Contract issues

- Backend unhandled errors return Flask HTML, while the frontend expects JSON with an `error` field.
- The catalog returns 500 for data failures while the frontend expects 503.
- `frontend/src/api/client.ts` defines a shared request wrapper, but no endpoint uses it. Requests are hand-written per function.
- The frontend does not use Zod schemas despite the technical design stating every response is parsed.
- Auth user ID types differ between layers.
- `backend/app/api/v1/README.md` advertises plans, transcripts, professors, and requirements modules that do not exist.

## 14. Testing, tooling, and documentation

### Missing tests

- `frontend/src/test/`, `frontend/e2e/`, and `backend/tests/` contain only README files.
- No test files exist anywhere in the repository.
- `package.json` has no `test`, `lint`, or `e2e` scripts.
- No Vitest, Testing Library, MSW, Playwright, ESLint, Zod, or React Hook Form dependencies are installed, although the technical design calls for them.
- `pytest` is declared for the backend, but there is no test suite or `conftest.py`.

### Migration issue

`backend/migrations/versions/6dd8d6e5f05f_add_user_fields.py:25` and `:27` add `credit_load` and `onboarded` as `nullable=False` without server defaults. This can fail on an existing nonempty users table. Add a server default or a safe backfill.

### Documentation drift

- Root `README.md` describes FastAPI, Better Auth, and `pdfplumber`, while the implementation uses Flask, custom opaque-cookie auth, and no parser.
- Root `README.md` says to create `backend/.env`, but the backend loads the repository root `.env`.
- Frontend `README.md` says every screen uses fake data, but profile and catalog use the real API.
- Frontend `README.md` says reset data uses `gp-mock-db`, while the code uses `gp-mock-db-v2`.
- `docs/design-rules.md` requires tests and tooling that are not configured.

### Done when

- Core plan rules, graph building, and term math have unit tests.
- Auth, profile, catalog, transcripts, and plans have backend tests.
- The three documented Playwright flows exist.
- `npm run lint` and `npm test` are real commands.
- Documentation matches the actual stack and environment loading.

## Prioritized completion plan

### P0: Make the core planner real

- [ ] Add models and migrations for plans, plan terms, plan courses, transcript courses, and generation jobs.
- [ ] Add `GET /summary`, `GET /plan`, `PUT /plan`, and `POST /plans/generate`.
- [ ] Add transcript upload, parser, OCR fallback, status polling, and parsed-course persistence.
- [ ] Persist manual coursework and skipped-coursework state.
- [ ] Generate a plan from the student's coursework, profile, and requirements.
- [ ] Replace mock `getSummary`, `getPlan`, `savePlan`, `generatePlan`, `getOptions`, and transcript functions with real API calls.
- [ ] Keep onboarding state until the generated plan is confirmed.
- [ ] Allow catalog-only courses to be added to a plan.
- [ ] Add tests for the full onboarding to dashboard flow.

**Exit criteria:** A new user can sign in, import or enter coursework, generate a personalized plan, see it on the dashboard, edit it in the flow chart, and reload without losing data.

### P1: Complete planning data and validation

- [ ] Import program requirements and map catalog requirement codes to user-facing categories.
- [ ] Add degree-progress calculation to the summary and dashboard.
- [ ] Implement prerequisite and concurrent-enrollment evaluation.
- [ ] Add offered-term and alternating-year rules to generation and validation.
- [ ] Add `GET /programs/:id/graph` and build the flow chart from real program data.
- [ ] Show prerequisite and concurrent conflicts before save.
- [ ] Expand the catalog beyond CSCI and MATH.
- [ ] Add professors, Rate My Professors, and course-specific Gopher Grades.
- [ ] Add the requirement filter and API-driven filter options.

**Exit criteria:** A plan is checked against real degree requirements, prerequisites, concurrent rules, and offered terms before it is saved.

### P2: Complete the documented product surfaces

- [ ] Add saved-plan list, create, rename, load, and delete.
- [ ] Add the unsaved-change navigation blocker.
- [ ] Add the academic term filter and fix the flow-chart major selector.
- [ ] Add graph keyboard support and real pinch zoom, or remove the pinch claim.
- [ ] Add the Settings Saving state and consistent client and server validation.
- [ ] Make Reset demo data truthful or remove it from production.
- [ ] Add parsed-course correction and transcript failure recovery.
- [ ] Add loading, empty, error, and retry states for dashboard, settings, summary, and search.
- [ ] Add Terms and Privacy content or remove the links.
- [ ] Fix the Google configuration failure UI.

**Exit criteria:** Every documented screen state and control works without dead ends.

### P3: Hardening and maintenance

- [ ] Add seed and import scripts with catalog version metadata.
- [ ] Add the in-memory cache for catalog and external integrations.
- [ ] Standardize JSON error responses and status codes.
- [ ] Add the shared request wrapper and response schemas.
- [ ] Fix the non-null migration with a server default or backfill.
- [ ] Add backend tests for auth, profile, catalog, transcripts, plans, and migrations.
- [ ] Add frontend unit, component, and end-to-end tests.
- [ ] Add linting and accessibility checks.
- [ ] Reconcile the README, design docs, and actual stack.

**Exit criteria:** CI can verify the core flows, and every team member can set up and test the project from the documented commands.

## Open decisions

1. **Single plan or multiple plans?** The current UI assumes one plan. Saved plans are documented as a feature but have no data model.
2. **Synchronous or asynchronous generation?** The design says the API returns a job ID. A synchronous response would be simpler but changes the contract.
3. **Where do degree requirements come from?** The catalog currently has course-level requirement codes but no program requirement trees.
4. **How is professor history collected?** This is the main external data dependency.
5. **What is the Gopher Grades URL contract?** The current generic link is not course-specific.
6. **Do we keep custom opaque-cookie auth?** The README says Better Auth, while the implementation is a working custom flow. Pick one and update the docs.
7. **What happens to the seeded demo plan?** It should not ship as the default plan for real users.

## Recommended order of work

1. Plan and transcript data models, migrations, and endpoints.
2. Onboarding persistence and server-side generation.
3. Real dashboard and flow-chart data.
4. Catalog add-to-plan and complete filters.
5. Programs, requirements, and prerequisite validation.
6. Professors, RMP, and Gopher Grades.
7. Settings and state polish.
8. Tests, linting, seed scripts, caching, and documentation cleanup.
