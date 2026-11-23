# Handoff: plan accuracy, sample plans, editing (2026-11-23)

Branch `full-stack-revamp`. Nothing is committed. Read `AGENTS.md`, `.claude/CLAUDE.md`, `README.md` and `docs/design-rules.md` (frontend) first.

## Rules

- Write tests first (TDD), and run a mutation check on any new logic.
- Use only synthetic data in tests and fixtures. Never use the real APAS PDFs.
- Never log transcript contents or student data.
- Change the schema only through Alembic. Never edit `backend/data/courses.db`.
- Check ownership at both the route and the service.
- Don't hold a DB session across slow work.
- No em dashes in text or code.
- Don't attribute anything to an AI tool in commits, PRs, code or docs.
- No git writes unless the user asks.
- Never print `.env` secrets. Never point `TEST_DATABASE_URL` at Supabase.

## Running things

- **Backend tests:** from `backend`, run `uv run pytest -q`. For Postgres, set `TEST_DATABASE_URL=postgresql+psycopg://gp:synthetic@localhost:55432/gp_test` (Docker container `gopher-test-pg`).
- **Frontend:** from `frontend`, run `npx vitest run` and `npx tsc -b --noEmit`. Use PowerShell, not Git Bash, for Vitest.
- **Servers:**
  - backend: `uv run flask --app app run --port 5000`
  - frontend: `npm run dev -- --port 5174 --strictPort`
  - Vite proxies `/api` to the backend.
- **Supabase:** `backend/.env` holds `DATABASE_URL`, which points at the Supabase session pooler. Apply migrations with `uv run flask db upgrade`.

## Done in this session

1. **Generator ranking** (`backend/app/services/planning/generate.py`).
   - Course-pool candidates are ranked by, in order:
     1. the program's `preferredCourses`
     2. how many open rules the course counts toward
     3. the program's home subject (the most common subject in its rules)
     4. missing prerequisite credits
     5. course level
     6. course code
   - `any` branches are ranked by:
     1. existing evidence
     2. `preferred: true` or "(Preferred)" in the label
     3. fewest added credits
     4. source order
   - The schema (`app/schemas/programs.py`) allows a `preferred` rule flag and a program-level `preferredCourses`.
   - The builder (`scripts/build_programs.py`) supports the overlay keys `preferredRules` and `preferredCourses`.
   - The CS overlay `scripts/program_overlays/019627107.json` prefers Physics II (`r-xk17L7jk`) and PHYS 1302W / 1402V. `data/programs/computer-science-bs--fall-2026.json` was rebuilt, and only that file changed.
2. **APAS transcript parser** (`app/parsers/transcript.py`: `parse_apas_text`).
   - It handles real APAS rows and noise from third-party OCR text layers. Unknown subjects are repaired against catalog codes.
   - `app/services/transcripts.py` re-runs local OCR when the text layer yields no rows or looks misread.
   - Uploads store `transcripts.not_imported` (migration `d3f8a2c61b74`) and return `notImported`.
3. **Full catalog.**
   - `scripts/export_courses.py` adds `le_attributes` and `description`. The export is `data/catalog-exports/courses.2026-11-23.csv`.
   - Migration `e9a1c47b2d58` adds `catalog_courses.le_attributes`.
   - `import_catalog(..., extra_csv=...)` merges the CSV and fills `le_attributes` and descriptions on the reviewed CSCI and MATH rows too.
   - Supabase is migrated through `e9a1c47b2d58` and re-imported: 25,707 courses.
   - `/courses` returns `leAttributes`.
   - `scripts/validate_programs.py` checks program courses against the catalog.
   - Majors without a review show an "unverified" note (`reviewed` flag on `/programs`).
4. **Sample plans.**
   - `scripts/export_sample_plans.py` exports `data/catalog-exports/sample-plans.2026-11-23.csv`: 161 pages, of which 130 parsed.
   - `scripts/build_sample_plans.py` writes `data/sample_plans/<program-id>.json`: 123 programs. Each holds terms of items: `course`, `choice`, `le` (categories use catalog designation names) or `elective`.
5. **Engine seeding.**
   - `app/services/planning/sample.py` provides `load_sample_plan(program_id)` and `sample_terms(graduation)`.
   - `Planner.seed()` runs before `run()`. It places sample courses in their mapped term, skips past terms and courses whose requirement is already met, and fills LE slots via the `le_suggest` callback unless `le_coverage` already covers them.
   - `generate_plan(..., sample=, graduation=, le_suggest=, le_coverage=)` returns placements with an optional `slot`, plus `electiveCredits` and `metadata` for the suggested courses.
   - Tests are in `tests/test_planning.py`.
6. **Catalog LE helpers** (`app/repositories/catalog.py`): `le_coverage(codes)` and `suggest_le_course(categories, season=, exclude=)`.
7. **Plan slot storage.**
   - Migration `f2b6d8e04a13` adds `plan_courses.slot`. It is NOT yet applied to Supabase.
   - `replace_planned_courses(..., slots=None)` keeps existing labels when `slots` is omitted. `planned_slots(user_id)` reads them.
8. **Frontend.**
   - The Settings demo controls are removed.
   - `src/features/coursework/CourseworkEditor.tsx` is in Settings (edit, remove, add, save, re-upload APAS), with tests.
   - Gen-ed suggestions show on the course drawer for text-only prerequisites.

The last full backend run before steps 6 and 7 was green: 469 passed. Re-run the full suites first.

## Remaining work

### 1. Wire seeding into `POST /plan/generate` (`app/services/plan.py`, `generate()`)

- Load `load_sample_plan(program["id"])`.
- Pass `graduation=user.graduation_target`.
- Pass `le_coverage=le_coverage(done and in-progress codes)`.
- Pass `le_suggest=lambda categories, term, exclude: ...`. It calls `suggest_le_course(categories, season=term.split()[0], exclude=exclude)`, then `resolve_course(code, program, find_courses([code])[code])`, and returns `(code, record, covered)`.
- Include every sample-plan course code in the `gather_metadata` call.
- Persist `slots={p["code"]: p["slot"] for p in placements if "slot" in p}` via `replace_planned_courses`.
- `build_plan`: add `"slot"` to each course (from `planned_slots`) and `"electiveCredits": max(0, totalCredits - projected)` to the Plan payload. Update `frontend/src/api/types.ts`.
- Keep doing DB reads before generation and writes after it. Don't hold a session across slow work.
- Tests: an API test with a synthetic sample plan via `SAMPLE_PLAN_DATA_PATH` and the synthetic catalog fixture. Assert that LE slots appear with a label, that covered categories are not re-planned, and that dry runs write nothing.
- Then run `uv run flask db upgrade` against Supabase to apply `f2b6d8e04a13`.

**Acceptance:**
- Generate the plan from the parsed CS audit (completed and in progress as in APAS; graduation Spring 2029). The schedule should contain no duplicates of completed or registered courses.
- Physics II is PHYS 1302W.
- Technical electives are CSCI.
- Missing LE categories have one suggested course each.
- `electiveCredits` is reported.

### 2. Flow chart "click to move" (frontend `src/screens/flow-chart/`)

- Click a planned course to open a menu or drawer with:
  - **Move to term:** a list of window terms. Disable invalid terms and say why (prerequisite order, season offered, credit load). Use the existing `planRules.ts` checks and `PUT /plan` changes.
  - **Remove from plan.**
  - For slot courses (`slot` set): **Swap suggestion**. List other courses for that LE category: add a `GET /courses?le=<category>` filter (backend `search_courses`, with a test), then replace via plan changes and keep the slot label.
- Must be keyboard accessible and work on mobile. Follow `docs/design-rules.md`. Announce changes in the existing live region. Tests go in Vitest.

### 3. Show slots and electives in the UI

- The dashboard and flow chart show a small "Gen ed: <label>" tag on slot courses.
- Add a line: "N free elective credits still needed" when `electiveCredits > 0`.

### 4. Sample plan coverage gaps

- 31 pages produced no rows because they use a different layout. The list is printed by the exporter. Inspect a few with view-source, extend `parse_plan_page` with tests, re-export, then rebuild with `build_sample_plans.py`.
- 7 pages are unmatched by name (see the builder output). Add an explicit slug-to-program-id map in `build_sample_plans.py` for real matches only.

### 5. Docs

- Update `README.md` (data sources: sample plans, new course export, import command `--csv data/catalog-exports/courses.2026-11-23.csv`), `backend/data/README.md` and `docs/feature-audit.md` (plan generation now sample-plan seeded; LE suggestions).
- Note in the docs that free electives are reported as credits and are not placed.

### 6. Later (separate issue)

Scrape https://schedulebuilder.umn.edu/ for sections and instructors (professors feature). Ask the user about terms, rate limits and storage before starting.

## Known limits to keep honest in the UI

- Only CS is hand-reviewed. Other majors show "unverified".
- Prerequisites outside CSCI and MATH are text only: they warn and never block (GitHub issue #13).
- A full OCR read of an image-only APAS takes about 60 s.
