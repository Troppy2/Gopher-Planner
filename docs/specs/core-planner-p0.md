# Spec: Make the Core Planner Real (audit P0)

**Status:** Slices 0 through 10 implemented on 2026-11-22; see the running report for verified results and open issues
**Source:** `docs/feature-audit.md`, section "P0: Make the core planner real"
**Method:** test-driven development, in vertical slices
**Revision:** 2026-11-07. Supabase hosts PostgreSQL; Flask remains the backend. Accurate, versioned academic requirements replace the original simplified groups. [Program requirements v2](program-requirements-v2.md) is binding wherever the original flat-group design conflicts with it.

**Resume point:** Slices 0 through 2 are implemented. Slice 3 calculations and per-user API are implemented; selected-program lookup waits for Slice 4. Complete the new [Slice 3.5 consolidation gate](branch-consolidation-slice-3-5.md) before Slice 4. Branch review and planning only were added on 2026-11-22; coding remains paused. Last backend run: 104 passed. Frontend typecheck/build have a recorded pre-existing TS7006 error in `GoogleSignInButton.tsx:32`. See [the running report](../core-planner-p0-report.md) for commands, files, red/green evidence, reviews, and remaining work. Preserve all existing tests and working-tree changes. No implementation of this revision has started.

**Continuation update, 2026-11-22:** the user resumed coding, completed the functional Slice 3.5 consolidation checks, supplied course data and requested a refreshable all-program source CSV. The snapshot contains 880 listed Twin Cities programs. The user then explicitly expanded planning to **all undergraduate majors**, excluding graduate/professional programs. This overrides the original single-major scope below. Source snapshots are not validated planner rules; preserve v2 semantics, version confirmation, provenance and review states while mapping supported undergraduate programs. Continue Slices 4 through 10 in order. The running report records actual test counts and the earlier TDD deviations; the prior resume paragraph is historical.

## 1. Goal

A new user can sign in, enter or import coursework, generate a personalized plan, see it on the dashboard, edit it in the flow chart, and reload without losing anything.

At the audited baseline, coursework, plans, summary and generation were mocked in the browser (`frontend/src/api/endpoints.ts`) and the backend had no plan or coursework model. This spec replaces those mocks with a real, tested backend and wires the frontend to it. The resume note above and running report distinguish work already implemented from the remaining slices.

Exit criteria (from the audit):

- Coursework persists (manual entry, skip state, and transcript import) and survives a refresh.
- `POST /plans/generate` builds a plan from the profile, coursework and program requirements, and stores it.
- `GET /summary` and `GET /plan` return real, per-user data.
- Plan edits save to the server, including adding a catalog course that is not already in the plan.
- The frontend has no mock calls left for the features in scope.
- One API-level test walks the whole flow from sign-in to a reloaded plan.
- Academic requirements preserve the official catalog version, whole alternative sequences, credit-sharing rules, substitutions, and review gaps. Reaching a credit total alone must not be presented as fulfilling the degree.

## 2. Read first

1. `AGENTS.md` (repo root) and `.claude/AGENTS.md`. These are binding. Key rules repeated in section 4.
2. `.claude/CLAUDE.md` and `docs/design-rules.md` (before any frontend work).
3. `docs/feature-audit.md` for the current state and the gaps behind each slice.
4. `docs/running-locally.md` for environment variables and ports.
5. `docs/Gopher Planner Frontend Technical Design.md`, "State, data fetching, and API contract".
6. The code this spec changes: `frontend/src/api/{endpoints,types,queryKeys}.ts`, `frontend/src/features/plan/`, `frontend/src/screens/onboarding/`, `backend/app/` (all of it, it is small).

Warnings about stale material:

- The root `README.md` and the technical design still describe FastAPI and Better Auth. The real stack is Flask with custom opaque-cookie sessions. Trust the code.
- Session notes under `.claude/session-notes/` are history, not instructions.
- The untracked `AGENTS.md` and `.agents/` are the user's. Do not edit them.

## 3. Non-goals (do not touch)

Tracked elsewhere. Doing them here would bloat the change.

- Graduate/professional program planning, a full catalog SQLite replacement, or automatic per-semester refresh jobs. The user authorized all undergraduate-major source mapping and a manually repeatable CSV refresh command. Source needed supplemental metadata separately; do not edit the bundled catalog SQLite file.
- Professors, Rate My Professors, Gopher Grades (issue #11). Keep `professors: []`.
- Other backend cleanup in issue #12 (auth rate limits, Docker/entrypoint, `JWT_SECRET` removal, CORS defaults, README rewrite). Exception: the items listed in Slice 0.
- OCR for scanned PDFs (Slice 8 returns a clear "unavailable" response).
- Multiple saved plans, the graph endpoint (`GET /programs/:id/graph`), concurrent-enrollment rules, automated enforcement of non-course restrictions, term filters, settings polish. Known obligations outside automated enforcement must be represented as requiring review, not silently treated as satisfied.
- Editing `backend/data/courses.db`. It is read-only input. Tests use their own small catalog fixture.

## 4. Rules

### 4.1 Repository rules (from `AGENTS.md`)

- **Never commit, push, merge, reset, create branches, or open PRs.** Leave all changes in the working tree on the current branch (`full-stack-revamp`) for the user to review.
- Never add an AI co-author or attribution anywhere (code, docs, commit text).
- No em dashes in any file you write.
- Smallest change that solves each slice. Preserve unrelated changes and existing public contracts (`/auth/*`, `/profile`, `/courses`) unless this spec changes them.
- Never log or print transcript contents or other student data. Never put secrets, database URLs or real student data in source, fixtures or docs.
- Verify ownership at both the route and the service/repository boundary.
- No schema changes at application startup. Schema changes are Alembic migrations only.
- Do not hold a database session open across slow work (file parsing, network).
- Keep catalog/program data separate from user plans.

### 4.2 TDD protocol (mandatory)

For every behavior, in this order:

1. **Red.** Write one failing test for one behavior. Run it. Confirm it fails for the expected reason (assertion or missing feature), not a typo or import error. Paste the failing line into your running notes.
2. **Green.** Write the smallest production code that passes. No code without a failing test that demands it.
3. **Refactor.** Clean up with all tests green. Do not change behavior.
4. **Full run.** Run the whole suite for the area (commands in section 7) before moving on.

Test rules:

- One behavior per test. Name tests as sentences: `test_put_plan_rejects_course_whose_prerequisite_is_planned_later`.
- Use a real database, not a mocked one. Backend tests run against SQLite built by applying the Alembic migrations (this also tests the migrations).
- Mock only what is external: Google token verification, the clock, and the filesystem when needed. Never mock your own services to make a test pass.
- Pure logic (terms, GPA, prerequisites, eligibility, generation, transcript text parsing) gets plain unit tests with no Flask app.
- Every user-owned resource gets a two-user test proving user B cannot read, change or delete user A's data. Another user's resource returns 404, not 403.
- Do not skip, `xfail`, delete or weaken a test to get green. If a test is wrong, fix the test and say why in the report.
- After a slice is green, pick one important assertion and temporarily break the implementation to confirm the test fails. Restore it.
- Pre-existing failures are not yours to hide. Report them separately from failures you introduced.

### 4.3 Stop and ask the user if

- You need a real APAS or transcript sample (see Slice 8). Do not invent the format.
- You cannot source real program requirements from an official UMN page (see Slice 4). Do not invent academic requirements.
- Required course title/credits or an academic exception cannot be verified from the official sources. Do not invent metadata, enable advisor-only exceptions automatically, or replace the degree with an easier pathway. Use explicit review states for known obligations outside automation, as described in the v2 contract.
- A slice needs a dependency or breaking API change not listed here.
- A test reveals the existing `/auth`, `/profile` or `/courses` behavior is wrong in a way that is not part of this spec.
- Anything would require a git write operation, a force operation, or deleting user files.

## 5. Decisions already made (use these defaults)

| Topic | Decision |
| --- | --- |
| User data | Supabase-hosted PostgreSQL through Flask, SQLAlchemy and psycopg. Existing Google authentication and opaque-cookie sessions remain. No Supabase SDK or Auth migration. Local SQLite tests remain migration-backed. |
| Plans per user | One. A `plans` row per user, unique on `user_id`. |
| Generation | Synchronous. The response keeps a `jobId` for contract compatibility, but there is no jobs table. Revisit only if generation takes more than about 2 seconds. |
| Transcript parsing | Synchronous inside the upload request. The PDF is not stored; only the extracted course rows are. Status values stay `parsing`, `parsed`, `no_text`, `failed`. |
| OCR | Implemented after P0 (2026-11-23): an upload with no text layer is read with local OCR (RapidOCR) during `POST /transcripts`; the `/ocr` retry route was removed because the PDF is never stored. `no_text` now means OCR also found nothing. |
| Program requirements | Versioned v2 JSON files in `backend/data/programs/`, with sourced expression trees, explicit sharing and substitutions. Not in `courses.db`. See [the v2 contract](program-requirements-v2.md). |
| Catalog version | Initially ship Fall 2026 for Computer Science B.S. Require explicit selection before persisting a generated program plan. Never mix catalog years. |
| Majors with no program file | Generation succeeds with no planned courses and the warning `program_requirements_unavailable`. Never a dead end in onboarding. |
| Prerequisite `condition` nodes (free text) | Retain nonblocking behavior, with a review warning. Missing prerequisite metadata is different from a verified empty prerequisite tree and blocks future placement. |
| Plan save validation | The server validates the whole resulting plan and rejects violations with 409. The frontend remains the first line of defense. |
| Status vocabulary | Reuse `done`, `prog`, `plan`, `avail`, `block`. Use `block` with a readable reason when a program course lacks scheduling metadata. |
| Terms | Only Fall and Spring terms are planned. Summer is ignored in the plan window. |
| JSON casing | camelCase on the wire, matching `frontend/src/api/types.ts`. |
| Error shape | `{"error": "<message>", "code": "<machine_code>"}`. `code` is new but additive; existing `{"error": ...}` consumers keep working. |
| Frontend test stack | Vitest, jsdom, Testing Library, user-event, jest-dom, MSW (listed in the technical design). Added as dev dependencies in Slice 9. |

## 6. Wire contracts

All routes are under `/api/v1`, require the `gp_session` cookie (401 `{"error": "Not signed in"}` otherwise), and state-changing routes also require the allowed `Origin` header (existing behavior). Field names and enums come from `frontend/src/api/types.ts`; do not rename them.

### 6.1 Coursework

`CourseworkEntry`:

```json
{ "code": "CSCI 1133", "title": "Intro to Computing", "credits": 4,
  "status": "done", "term": "Fall 2025", "grade": "A-", "source": "manual" }
```

| Field | Rules |
| --- | --- |
| `code` | Matches `^[A-Z]{2,6} \d{4}[A-Z]?$`. Need not exist in the catalog (the catalog only has CSCI and MATH today). |
| `title` | String, 1 to 255 characters. |
| `credits` | Number, greater than 0 and at most 12, in steps of 0.5. |
| `status` | `done` or `prog`. |
| `term` | `"Fall 2025"` style or `null` (unknown). Must be `null` or a valid `Season YYYY` string. |
| `grade` | `null` or one of `A, A-, B+, B, B-, C+, C, C-, D+, D, F, S, N, W, I`. A `prog` entry must have `grade: null`. |
| `source` | `manual` or `transcript`. Server-controlled; ignored on input except to preserve existing values. |

- `GET /coursework` returns `{"courses": [CourseworkEntry], "skipped": false}`.
- `PUT /coursework` body `{"courses": [CourseworkEntry], "skipped": false}` replaces the user's whole set atomically. At most 300 entries. Duplicate `(code, term)` pairs are 400. Returns the same shape as GET.

### 6.2 Summary

`GET /summary` returns the `Summary` type:

```json
{ "gpa": 3.62, "gradedCredits": 48, "creditsCompleted": 74, "creditsTotal": 120,
  "percentComplete": 62, "program": "Computer Science B.S.", "source": "Based on your transcript" }
```

- `gpa` is `null` when there are no graded credits. `percentComplete` is `null` when the user has no coursework rows, otherwise an integer capped at 100.
- `creditsTotal` is the program's `totalCredits`, or 120 when the program is unknown.
- `source` is `"Based on your transcript"` if any row has source `transcript`, `"Based on the courses you entered"` if only manual rows exist, `""` otherwise.
- `percentComplete` measures credit progress. Degree-requirement progress is separate in the Plan v2 additions; 100% credits does not mean the degree requirements are satisfied.

### 6.3 Plan

`GET /plan` returns the existing core `Plan` fields plus the additive v2 fields defined below:

```json
{ "terms": ["Completed", "Fall 2026", "Spring 2027"], "currentTerm": "Fall 2026",e
  "baseCredits": 0, "courses": [ /* Course */ ] }
```

How it is built:

- `terms`: `"Completed"`, the current term, then future terms. The window extends to the user's `graduationTarget` if it is a valid future term, otherwise 8 future terms. Maximum 12 future terms.
- `courses` contains the union of courses referenced by the selected program's expressions and any catalog or program-metadata course the user added. Alternatives appear as options, not as universally required courses. Status is `done`, `prog`, `plan`, `avail`, or metadata-blocked `block`.
- `baseCredits` counts earned credits from completed coursework outside `courses` (transfer, AP, electives outside the program), applying the summary's passing-grade rules and v2 duplicate-evidence safeguards. Failed or withdrawn rows cannot inflate the graduation-credit projection.
- Select course metadata using the v2 catalog-version/provenance rules. Compatible verified catalog facts take precedence; target-version supplemental facts override unknown-version or mismatched legacy facts. Conflicts require review. Coursework credits take precedence for completed/current rows. Flat `prereqs` are display data; eligibility evaluates the full prerequisite tree. `requirement` is a presentation category, using category priority when a code belongs to multiple groups; the engine must retain every actual membership. Outside-program additions default to `Elective`. Keep `concurrent: []` and `professors: []`.
- Add `catalogTerm`, `availableCatalogTerms`, `warnings`, and `requirementProgress` to Plan, and `metadataSource`/`metadataWarnings` to Course. The v2 contract defines their semantics. `availableCatalogTerms` is a list from the program loader, empty for an unknown major. These fields must be returned consistently by GET, PUT, dry run and persisted generation.
- Completed or in-progress courses always appear in the term they were taken, or in `"Completed"` when the term is unknown.

`PUT /plan` body:

```json
{ "changes": [ { "code": "CSCI 2041", "status": "plan", "term": "Spring 2027" },
               { "code": "MATH 2243", "status": "avail", "term": null } ] }
```

- `status: "plan"` adds or moves a course into a future term. `status: "avail"` with `term: null` removes it from the plan.
- Any catalog or selected-program supplemental course may be added, not only courses already in the plan. Metadata-blocked courses cannot be placed.
- PUT additionally accepts optional `catalogTerm`. Use the saved plan's version when omitted. A known program with no confirmed version cannot be saved without one: return 400 `program_version_unconfirmed`. An unsupported requested version returns 400 `program_version_unavailable`, with no writes. Unknown-major catalog-only plans remain valid without a version. Dry-run drafts must carry their selected term into save.
- The batch is atomic. Returns the full `Plan` on success.
- 400 `invalid_change`: unknown field, status other than `plan` or `avail`, a term that is `Completed`, the current term or outside the window, or `plan` without a term.
- 404 `unknown_course`: the code is known to neither the catalog nor the selected program metadata (only when adding).
- 409 `plan_invalid`: the resulting plan breaks a rule. Body: `{"error": "...", "code": "plan_invalid", "violations": [{"code": "CSCI 2041", "reason": "prerequisite_not_before", "detail": "CSCI 1933"}]}`. Reasons: `not_offered_in_season`, `prerequisite_not_before`, `locked_course` (editing a `done` or `prog` course).
- Add violation reason `course_metadata_unavailable` for unavailable prerequisite metadata. An incomplete set of degree requirements is progress information, not by itself a reason to reject a partially built plan.
- Nothing is persisted when the response is not 200. Version selection and course changes persist atomically; never silently drop saved courses when a version changes.

### 6.4 Generate

`POST /plans/generate` body `{"dryRun": false, "catalogTerm": "Fall 2026"}` (body optional). `catalogTerm` is optional when the saved plan already has a confirmed version or the major is unknown. See the v2 contract for unconfirmed-version behavior.

```json
{ "jobId": "uuid", "status": "succeeded", "warnings": [], "plan": { /* Plan */ } }
```

- `dryRun: false` replaces all of the user's `plan_courses` with the generated set and stores them. `dryRun: true` returns the plan without writing anything (used by the flow chart Build button, which shows the result as an unsaved draft).
- Warnings include the existing codes and the v2 version, requirement-review, and metadata codes. A successful generation envelope means computation succeeded, not that graduation eligibility is certified. An unconfirmed version writes nothing and returns `program_version_unconfirmed` with no placements; the UI asks for a supported term.
- On unexpected failure: 500 `{"error": "...", "code": "generation_failed"}` and no partial writes.

### 6.5 Transcripts

- `POST /transcripts`, multipart field `file`. Accepts only PDFs (starts with `%PDF`), maximum 10 MB. 400 `missing_file`, 415 `not_a_pdf`, 413 `too_large`. Returns 201 `{"id": "<uuid>"}`.
- `GET /transcripts/:id` returns the `Transcript` type plus the parsed rows:

```json
{ "id": "uuid", "fileName": "apas.pdf", "status": "parsed",
  "completed": 24, "inProgress": 4, "courses": [ /* CourseworkEntry */ ] }
```

- Parsed rows are stored as coursework with `source: "transcript"`. A re-upload replaces the user's previous transcript rows and keeps manual rows.
- `status: "no_text"` when the PDF has no extractable text. `status: "failed"` when text exists but nothing could be parsed, with `"errorCode"` (`unrecognized_format`).
- `POST /transcripts/:id/ocr` returns 501 `ocr_unavailable`.
- A transcript belonging to another user returns 404.

### 6.6 Data model

Create with Alembic migrations (backend, SQLAlchemy 2 style matching the existing models). Must work on both SQLite and PostgreSQL. Names are suggestions; keep columns and constraints.

| Table | Columns and constraints |
| --- | --- |
| `coursework` | `id`, `user_id` FK users ON DELETE CASCADE (indexed), `code`, `title`, `credits` Numeric(4,1), `status`, `term` nullable, `grade` nullable, `source`, `transcript_id` nullable FK transcripts ON DELETE SET NULL, timestamps. Unique `(user_id, code, term)`. |
| `transcripts` | `id` (uuid string), `user_id` FK CASCADE, `file_name`, `status`, `error_code` nullable, `created_at`. |
| `plans` | `id`, `user_id` unique FK CASCADE, `generated_at` nullable, timestamps; add nullable `catalog_term` in the separate Slice 4 revision. Do not rewrite the Slice 1 revision for this addition. |
| `plan_courses` | `id`, `plan_id` FK CASCADE, `code`, `term`, `source` (`generated` or `user`). Unique `(plan_id, code)`. |
| `users` | add `coursework_skipped` Boolean NOT NULL with `server_default` false. |

Every new NOT NULL column added to an existing table needs a `server_default` so the migration works on a table that already has rows.

### 6.7 Academic requirements v2

[Program requirements v2](program-requirements-v2.md) defines the versioned data schema, expression types, evidence allocation, grade qualification, adjustments, missing catalog metadata, progress fields, warnings, and required tests. It supersedes the old flat-group behavior in Slices 4 through 9. Keep the existing summary wire fields and auth/profile/catalog contracts; implement the documented plan/generation additions test-first.

## 7. Commands

Backend (from `backend/`, Windows PowerShell or any shell):

```text
uv run pytest -q                       # full backend suite
uv run pytest tests/path -q -k name    # one test
uv run flask --app app db upgrade      # against a throwaway SQLite DATABASE_URL, never the user's real DB
```

Frontend (from `frontend/`):

```text
npm run typecheck
npm test                               # after Slice 9 adds it
npm run build
```

Run the narrowest check first, then the full suite for the area, then the build.

## 8. Slices

Do the slices in order. Each slice ends with: all tests green, no unrelated files changed, and a short report entry (section 10). Continue to the next slice unless a stop condition in 4.3 applies.

---

### Slice 0: Test harness and shared plumbing

**Why:** nothing else can be test-driven without it, and the audit's migration bug blocks upgrading a populated database.

Tests first:

- `/health` returns `{"status": "ok"}`.
- Each of `/profile`, `/courses`, `/summary` returns 401 JSON without a session.
- Characterization tests for current behavior before any refactor: sign-in rejects non-UMN and unverified emails (Google verification mocked), expired and revoked sessions are rejected, a wrong `Origin` gets 403, profile validation errors, and `/courses` filters and pagination against the small catalog fixture.
- Migrations: `upgrade head` on an empty SQLite database succeeds; downgrade to base succeeds; applying migrations then running Alembic autogenerate comparison reports **no drift** between models and migrations.
- Migration `6dd8d6e5f05f`: with a `users` row already present at the previous revision, `upgrade head` succeeds (needs `server_default`s on `credit_load` and `onboarded`). Edit that migration in place; mention this in the report because it rewrites an existing revision.
- Unknown route and wrong method return JSON (`404` and `405`) with `{"error", "code"}`, and an oversized upload returns JSON 413, not Flask's HTML page. An unhandled exception returns JSON 500 and logs the stack trace without request bodies.

Build:

- `backend/tests/conftest.py`: sets required env vars (including `GOOGLE_CLIENT_ID` and `JWT_SECRET` while they are still required), points `DATABASE_URL` at a temp SQLite file, builds the schema by running migrations, and provides `app`, `client`, `make_user(email=...)`, `login_as(user)` (inserts a `UserSession` and sets the `gp_session` cookie directly, no Google call), `post_headers` (the allowed `Origin`), a settable clock, and a tiny catalog fixture database (same schema as `courses.db`, a dozen courses with prerequisite JSON covering `course`, `any_of`, `all_of` and `condition` nodes).
- Add `[tool.pytest.ini_options]` to `backend/pyproject.toml`.
- `CATALOG_DB_PATH` environment override for the catalog location, defaulting to the current `backend/data/courses.db`. Read through `app/repositories/catalog.py` (read-only, opened the same way as `open_catalog()` today). New code uses the repository; leave existing `/courses` handlers working.
- `app/core/auth.py`: move `read_session`, `check_request_origin` and a new `require_auth` decorator out of `api/v1/auth.py` so other modules stop importing from it. Behavior-preserving: the characterization tests above must pass before and after.
- JSON error handlers registered in `create_app`.

Done when: harness and characterization tests pass, drift test passes, and the populated-database migration test passes.

---

### Slice 1: Models and migrations

Tests first (against migrated SQLite):

- Inserting each new model works; constraints hold (`coursework` unique `(user_id, code, term)`, `plan_courses` unique `(plan_id, code)`, `plans.user_id` unique).
- Deleting a user cascades to their coursework, transcripts and plan rows.
- Deleting a transcript sets `coursework.transcript_id` to null, not delete the rows.
- `users.coursework_skipped` defaults to false for existing users.
- The drift test from Slice 0 still passes.

Build: models under `app/models/`, one Alembic revision (`flask db migrate`, then review and edit the generated file; autogenerate output is a draft). Export in `app/models/__init__.py`.

Done when: upgrade, downgrade and drift tests pass on SQLite. If PostgreSQL is available locally, also run the upgrade there and report it; do not require it.

---

### Slice 2: Coursework API

Tests first:

- GET returns `{"courses": [], "skipped": false}` for a new user.
- PUT stores entries and GET returns them with `source: "manual"`.
- PUT replaces the previous set (removing an entry removes the row).
- PUT sets `skipped`, and skipped plus an empty list is valid.
- Validation: bad code format, `credits` of 0, 13 or 0.3, unknown grade, `prog` with a grade, malformed term string, duplicate `(code, term)`, more than 300 entries, non-list body, unknown extra fields. Each returns 400 with `code` and leaves stored data unchanged.
- Rows with `source: "transcript"` survive a PUT that includes them unchanged and keep their source.
- Ownership: user B's GET never contains user A's rows; user B's PUT never touches user A's rows.
- Unauthenticated and wrong-origin requests are rejected like other routes.

Build: `app/schemas/coursework.py` (validation), `app/services/coursework.py`, `app/api/v1/coursework.py`, blueprint registered.

Done when: all tests green.

---

### Slice 3: Summary

Tests first (pure unit tests for the maths, then API tests):

- UMN grade points: `A 4.000, A- 3.667, B+ 3.333, B 3.000, B- 2.667, C+ 2.333, C 2.000, C- 1.667, D+ 1.333, D 1.000, F 0.000`. Keep the table in one constant. **Verify it against the University of Minnesota registrar's published scale before relying on it, and cite the page in a code comment.**
- GPA is credit-weighted over graded `done` rows only (`A` through `F`).
- Credits completed count passing grades (`A` through `D`, and `S`) and ungraded `done` rows; `F`, `N`, `W`, `I` earn nothing. `S` and `N` and `W` and `I` are excluded from GPA.
- `prog` rows never count as completed.
- `gradedCredits` is the credit sum used in the GPA.
- Empty coursework: `gpa` null, `percentComplete` null, `creditsCompleted` 0.
- `percentComplete` is rounded and capped at 100; `creditsTotal` comes from the user's program or 120.
- `source` and `program` follow section 6.2.
- Ownership: summaries are computed only from the signed-in user's rows.

Build: `app/services/summary.py` (pure functions) and `GET /summary`.

---

### Slice 3.5: Clean up and consolidate branch work

Follow the binding [branch inventory and TDD consolidation plan](branch-consolidation-slice-3-5.md). Review the available teammate work against our uncommitted implementation, retain compatible behaviors through section 4.2, and schedule parser/plan/frontend reuse in the appropriate later slices. Preserve our canonical models, contracts and v2 requirements. No wholesale merge or branch checkout is authorized.

Tests first: characterize existing coverage, then verify nullable-term attempt uniqueness at the database boundary. Add only a missing constraint demanded by a failing test, with a new migration and migration regression checks if needed. Do not introduce extra-credit models, replacement authentication, development identity APIs, raw transcript storage, or new dependencies.

Done when: branch freshness is verified, all candidate behaviors have a recorded disposition, any adopted behavior has red/green and mutation evidence, full backend checks pass, and the running report records remaining PostgreSQL/frontend limitations. The initial review used cached refs because GitHub was unreachable; freshness remains a gate. Implementation remains paused until the next coding session.

---

### Slice 4: Programs and requirements loader

**Do not invent academic requirements.** Implement the schema and semantics in [Program requirements v2](program-requirements-v2.md). Source one Fall 2026 Computer Science B.S. file, preserving complete alternatives, shared-credit quotas, substitutions and grade policies. Source required supplemental course metadata separately from the read-only SQLite catalog. If a required academic fact cannot be verified, stop and ask under 4.3. Tests use synthetic files under `backend/tests/fixtures/programs/`, never the shipped real file or live web calls.

Tests first:

- Loader accepts a valid v2 file and resolves by major plus catalog term; it exposes supported terms without mixing versions. Unknown major returns `None`; unsupported requested term is distinguishable from an unknown major.
- Reject missing fields, unknown node/category types, malformed or empty trees/sets, invalid course codes, duplicate global IDs, missing source/set/metadata references, invalid credit/count bounds, invalid sharing declarations and adjustment cycles or ambiguous stacking.
- Loading is cached in memory by version; the cache can be cleared in tests.
- Pure requirement evaluation tests cover nested alternatives, complete sequence branches, credit/count quotas, source-permitted reuse, one-time waivers, grade thresholds, repeated evidence, and completed/projected/review states. Include the combined elective total with a subject subminimum and a math course counted inside that same total.
- Supplemental-only courses resolve title/credits correctly. Test compatible catalog precedence, target-version supplemental precedence over unknown legacy records, and conflicts between verified compatible sources. Unknown prerequisites differ from verified-empty prerequisites. Missing required title/credits cannot be replaced with guesses. The shipped SQLite catalog remains unchanged.
- Add a nullable `plans.catalog_term` migration and model field, with empty/populated upgrade, downgrade and no-drift tests. Preserve the original Slice 1 migration and tests.
- Integrate selected-program totals into `/summary`, with a synthetic non-120-credit program proving lookup works. Retain existing GPA and credit-math tests.

Build: `app/services/programs.py`, pure requirement-evaluation helpers, catalog/supplement metadata resolver, the plan-version migration, one sourced real program file, and `backend/data/README.md` format/source notes. No new dependency is authorized.

Done when: v2 loader/evaluator, supplemental metadata resolution, summary integration and migration tests pass, and every real-file rule is traceable to an official source and catalog version. A hand-selected easier pathway is not an acceptable substitute.

---

### Slice 5: Planning engine (pure Python, no Flask)

Port term and placement semantics from `frontend/src/features/plan/planRules.ts` to `app/services/planning/`, then extend them for full prerequisite trees and the v2 requirement evaluator. The original client greedy algorithm is not authoritative for degree completion or branch selection.

Modules and tests first:

- `terms.py`: `season(term)`, `current_term(today)`, `future_terms(start, count)`, `term_index`. Rules: months 1 to 5 map to `Spring {year}`, months 6 to 12 map to `Fall {year}`; the sequence after `Fall 2026` is `Spring 2027`, then `Fall 2027`; no Summer. Test the boundaries (May 31, June 1, December 31, January 1) and year rollover.
- `prerequisites.py`: evaluate a catalog prerequisite tree against `(done_before, in_progress, planned_before)`. `course` nodes need the course done, in progress, or planned in an earlier term; `all_of` needs every child; `any_of` needs one. Free-text conditions/unresolved references retain nonblocking behavior but emit review warnings. A missing metadata record or unknown prerequisite expression is not evidence of no prerequisites. Test that distinction, nested trees, verified-empty trees and missing trees.
- `eligibility.py`: a course can be placed when its scheduling metadata is sufficient, it is not known to be absent that season, and prerequisites pass. Unknown offering information produces a tentative-placement warning. Missing prerequisite metadata blocks placement. Same-term prerequisites do **not** count; in-progress prerequisites count conditionally.
- `generate.py`: deterministic requirement-aware fill:
  - never places `done` or `prog` courses; clears previous `plan` placements first;
  - fills each future term up to `creditLoad`, never exceeding it;
  - select complete viable alternative branches using already-qualifying coursework first, then fewer additional credits, then stable branch ID. Try another complete branch when one cannot fit. Do not combine incomplete halves of alternatives;
  - within a selected branch, prioritize unmet requirements and their prerequisite closure, then category `Major core`, `Math and stats`, `Elective`, `Liberal ed`, then course code ascending;
  - re-evaluate quotas, sharing, grade assumptions and sourced adjustments after each addition; never inflate totals by adding overlapping child subtotals or the same course twice;
  - stop only when both the deduplicated projected credit goal and machine-checkable projected requirements are met, or no feasible additions remain. Report unsatisfied or review-only requirements explicitly;
  - never places a course before its prerequisites, in any term;
  - identical input always gives identical output;
  - emits the v2 requirement/metadata warnings plus `graduation_target_unreachable` when the credit goal is not reached by the last term. A heuristic failure is not proof that no valid schedule exists;
  - an unknown program yields no placements and `program_requirements_unavailable`; unsupported and unconfirmed versions also yield no placements with their distinct warnings.
- `validate.py`: given a full resulting plan, returns schedule violations used by `PUT /plan`: `not_offered_in_season`, `prerequisite_not_before`, `locked_course`, `course_metadata_unavailable`. Moving a prerequisite later flags its dependents. Degree incompleteness is progress information; it does not forbid saving a partial plan.

Test with small, hand-checkable synthetic course sets, including every rule above and the v2 acceptance cases. The four-term mini program must include nested alternatives, a shared-credit subminimum and an unavailable first-choice branch. Include a plan that reaches its credit goal while still missing a required course.

Done when: all unit tests pass with no Flask app or database involved.

---

### Slice 6: Plan read and write API

Tests first (API, with the catalog and program fixtures):

- GET with a confirmed version returns program options (`avail` or metadata-blocked `block`) and terms starting with `Completed` and the injected current term. Without confirmation, return null `catalogTerm`, supported terms, empty requirement progress, and a confirmation warning rather than silently loading one year's program. Existing user data remains readable.
- Coursework `done` and `prog` rows appear with those statuses; a completed course outside the program adds to `baseCredits` instead of appearing in `courses`.
- A `prog` course appears in the current term.
- `requirement`, `offered`, `prereqs`, `title` and `credits` come from the right sources (section 6.3).
- Test version-aware metadata precedence and sourced supplemental-only courses. GET/PUT return completed/projected requirement progress and retain metadata warnings after reload.
- Explicit catalog term persists with successful course changes. Missing confirmation or an unsupported requested term writes nothing. Dry-run version selection is not persisted until save. A version change never silently deletes courses or mixes requirements from different files.
- PUT adds a program course to a future term and GET reflects it.
- PUT adds a catalog course that is not in the program (the "catalog-only course" bug from the audit) and it appears with requirement `Elective`.
- PUT removes a planned course (`avail`, `null`).
- PUT 400 cases from section 6.3, each leaving stored data unchanged.
- PUT adds a supplemental-only program course when scheduling metadata is sufficient; PUT rejects incomplete prerequisite metadata with 409 `course_metadata_unavailable` inside `plan_invalid` violations. A code known to neither source returns 404 `unknown_course`.
- PUT 409 `plan_invalid` with the right `violations` for: wrong season, prerequisite planned in the same or a later term, editing a `done` or `prog` course. Batch atomicity: a batch with one valid and one invalid change persists neither.
- Moving a prerequisite later so a dependent now breaks is rejected naming the dependent.
- Ownership: user B never sees or changes user A's plan.
- Persisted rows have `source: "user"`; generated ones (Slice 7) have `source: "generated"`.

Build: `app/services/plan.py`, `app/repositories/plans.py`, `app/api/v1/plan.py`. The service owns validation; the route only translates.

---

### Slice 7: Generate API and the end-to-end API test

Tests first:

- `POST /plans/generate` for a user with profile, coursework and the fixture program returns 200, a `jobId`, `status: "succeeded"`, and a plan that matches the Slice 5 engine output; `GET /plan` afterwards returns the same plan.
- Re-running replaces previous generated placements and does not duplicate rows.
- `dryRun: true` returns a plan and writes nothing (row counts unchanged).
- Completed and in-progress coursework is excluded from future placement.
- The user's `creditLoad` and `graduationTarget` are respected.
- A confirmed catalog term round-trips; omitted unconfirmed and unsupported requested terms return distinct warnings and no writes. Update the flow test to explicitly confirm the synthetic program's catalog term.
- Generated progress uses complete alternatives, grade qualification, subject quotas, shared-credit accounting and justified waivers. Credit-target success with unmet requirements remains visibly incomplete. Missing metadata yields an honest partial plan, never invented prerequisites or offerings.
- Unknown major: 200, empty placements, warning `program_requirements_unavailable`.
- Engine exception: 500 `generation_failed` and no partial writes (inject a failure and compare row counts).
- Ownership: generating for user A never changes user B's plan.
- **Flow test (the audit exit criterion):** sign in, `PUT /profile`, `PUT /coursework`, `POST /plans/generate`, `GET /summary`, `GET /plan`, `PUT /plan` (add a catalog-only course), then build a fresh client with the same session cookie and confirm `GET /plan` and `GET /summary` return the saved state.

Build: `POST /plans/generate` and the persistence glue in `app/services/plan.py`.

---

### Slice 8: Transcript upload and parsing

**Requires a real, redacted sample.** The APAS/transcript layout is unknown to this spec. Build the pipeline and a parser against a clearly documented *synthetic* text format, mark the parser's line patterns as provisional, and ask the user for a redacted real sample before claiming the parser works on real documents. Never commit a real transcript or any real student data.

Dependencies: add `pdfplumber` (runtime) and a small PDF-generation library such as `reportlab` (dev only) with `uv add`.

Tests first:

- `parse_transcript_text(text) -> list[ParsedCourse]` is a pure function in `app/parsers/`: extracts code, title, credits, grade, term, and `done` or `prog`; tolerates blank lines and page headers; returns an empty list for unrecognized text; never raises on garbage input.
- The pdfplumber wrapper is separate from the parser and returns plain text (tested with a generated one-page PDF).
- API: valid generated PDF returns 201 then GET shows `parsed` with correct `completed` and `inProgress` counts and rows stored as `source: "transcript"`.
- A PDF with no text layer (an image-only or blank page) gives `no_text`.
- A PDF with text but no recognizable rows gives `failed` with `errorCode: "unrecognized_format"`.
- A non-PDF file gives 415; a missing file field gives 400; an oversize body gives 413.
- A re-upload replaces transcript rows and keeps manual rows.
- `POST /transcripts/:id/ocr` returns 501 `ocr_unavailable`.
- Ownership: another user's transcript id returns 404 on GET and OCR.
- **Privacy:** with log capture enabled, no log record contains any text from the uploaded PDF, and the stored `file_name` is a sanitized base name (no path separators), maximum 255 characters. The uploaded bytes are not written anywhere that persists after the request.
- The database session is not held while parsing (commit the transcript row first, parse, then write results).

Build: `app/parsers/`, `app/services/transcripts.py`, `app/api/v1/transcripts.py`.

---

### Slice 9: Frontend wiring

First add the test stack as dev dependencies in `frontend/`: `vitest`, `jsdom`, `@testing-library/react`, `@testing-library/user-event`, `@testing-library/jest-dom`, `msw`, plus a `test` script and a `vitest` config with a setup file and an MSW server. Mention the dependency change in the report.

Follow the same red, green, refactor loop with MSW handlers that mirror the contracts in section 6.

9a. **API layer** (`frontend/src/api/endpoints.ts`). Tests first, per function: correct URL, method, `credentials: "include"`, body shape, success parsing, and error mapping to `ApiError` (401 to `auth`, 400 and 409 to `validation` with the server message and `violations`, 404 to `not_found`, 5xx and network failures to `network`). Replace the mock bodies of `getSummary`, `getPlan`, `savePlan` (send `{changes}`), `generatePlan` (accept `{dryRun}`; return the new envelope), `uploadTranscript` (multipart `FormData`, no manual `Content-Type`), `getTranscript`, `retryTranscriptOcr`, and add `getCoursework` and `saveCoursework`. Use one shared request helper in `api/client.ts` for the new functions instead of copy-pasting `fetch`. Leave `getOptions` mocked with a comment pointing at issue #9. Update `api/types.ts` and `queryKeys.ts` as needed.

- Include optional `catalogTerm` in generate/save requests and model all v2 Plan/Course/progress additions. Obtain `availableCatalogTerms` from GET /plan, not hardcoded mock options. Dry-run drafts retain their selected term for the later save request.

9b. **Onboarding persistence.**

- Tests: continuing from the coursework step calls `saveCoursework` with the manual entries mapped to the contract (`done` or `prog`, credits from the catalog result, `term` null for `done`, current term for `prog`); choosing Skip calls it with `skipped: true`; a refresh on the profile step restores entries from `getCoursework`; a failed save shows an error and does not advance.
- Remove the dependency on the in-memory store as the only source of truth; the store may remain as a draft cache.
- Move the transcript query to the parent screen, as the audit recommends, instead of relying on the child to populate the cache key.

9c. **Transcript UI states.**

- Tests: upload progress reflects real request state (no fake 14 percent timer); `parsed` shows counts and the parsed rows for correction; `no_text` shows the scanned-PDF recovery; `failed` has its own visible state with a manual-entry path (currently it falls through to the spinner); a rejected upload is caught and shown; OCR retry that returns 501 offers manual entry instead of looping.

9d. **Building screen and dashboard.**

- Tests: `BuildingPlanScreen` calls the real generate, shows steps based on actual progress rather than fixed timers (a short minimum display time is fine), shows success, shows the failure state with Try again that really retries, shows the `program_requirements_unavailable` warning in words, and only then marks the user onboarded.
- Dashboard: summary loading shows skeletons and a missing value shows `N/A` (design rule in `docs/design-rules.md`), summary errors are visible, and values come from the server.
- For a known program without a saved catalog version, show supported terms and require explicit selection before generation. An unconfirmed version must not complete onboarding. Unsupported terms have a readable recovery path; unknown majors retain the existing warning-and-continue behavior.
- Show completed and projected requirement progress separately, including alternative branches, justified substitutions and review gaps. Label the percentage as credit progress; 100% credits must not hide unmet degree requirements or imply certified graduation eligibility. Translate every v2 warning into clear language.

9e. **Flow chart and catalog add-to-plan.**

- Tests (hook-level for `usePlan`, component-level for the buttons): `build()` calls generate with `dryRun: true` and turns the result into an unsaved draft; `add` works for a catalog course that is not in the saved plan, using a pure `catalogToPlanCourse` mapper (unit test it); the catalog results Add button and the course drawer both add a catalog-only course; a 409 from save restores the draft and shows the violation in words.
- Delete the client-side greedy `buildPlan` and its exports only if nothing else uses them after this change; otherwise leave them.
- Test supplemental-only course rendering/addition, metadata-blocked courses with disabled Add and a readable reason, and full prerequisite-tree eligibility. Flat display `prereqs` must not reintroduce an incorrect all-prerequisites interpretation of `any_of` branches. Honor the selected catalog version in both Build and Save.

9f. **Clean-up of mocks.** Remove mock paths only for the features in this spec. `getOptions`, Settings "Reset demo data" and the preview flags that belong to unrelated features stay, with a comment explaining why. Run a repository-wide search and report any remaining imports of `@/api/mock` and why each remains.

Done when: `npm run typecheck`, `npm test` and `npm run build` all pass.

---

### Slice 10: Documentation

- `docs/feature-audit.md`: update the status table and the affected sections to match reality (do not change the audit date or revision header; add a short "Updated" note listing what changed).
- `docs/running-locally.md`: add the `CATALOG_DB_PATH` variable, how to run the backend and frontend tests, and a manual smoke path (sign in, upload or enter coursework, build, edit, reload).
- `backend/data/README.md`: v2 program format, official source verification, catalog-version selection, supplemental metadata, and how to add a version without mixing requirements.
- Do not rewrite the root `README.md` (issue #12 owns that), but fix any statement your change makes false and say so in the report.

## 9. Definition of done

- Every slice's tests were written first and seen failing for the right reason.
- `uv run pytest -q` passes; migrations apply to an empty database and to one with existing users; the drift test passes.
- `npm run typecheck`, `npm test` and `npm run build` pass.
- No mock calls remain for coursework, summary, plan, generation and transcripts in the frontend.
- The shipped program uses the v2 contract and a verified official catalog version. Nested alternatives, quotas, sharing, grade qualification, adjustments and review-only obligations are tested. Program-only course metadata is sourced, not fabricated; the bundled catalog SQLite file remains unchanged.
- Persisted plans retain their selected catalog term. Unsupported/unconfirmed versions cannot silently write a generated plan. Completed and projected requirements remain distinct from total-credit progress in the API and UI.
- No transcript content in logs, fixtures or docs; no secrets added; no em dashes added.
- No git write operation was performed. The working tree is left for review.
- The final report (section 10) is complete and honest about gaps.

## 10. Report format

After each slice, add a short entry. At the end, give one summary containing:

1. Slices completed, with test counts (backend and frontend) and the exact commands you ran.
2. Files added or changed, grouped by slice.
3. Decisions you made that this spec did not cover, and why.
4. Anything you deviated from, with the reason.
5. Open issues: provisional parsers, missing data, failing or skipped checks (separating pre-existing failures from new ones), and anything needing the user's input (real transcript sample, program source).
6. The manual smoke steps for the user to run, and what you could not verify yourself (for example, real Google sign-in or PostgreSQL).
