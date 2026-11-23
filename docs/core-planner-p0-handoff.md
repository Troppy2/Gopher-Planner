# Gopher Planner P0 handoff

**Superseded 2026-11-22:** Slices 4 through 10 are now implemented. The current state, open issues and smoke path are in the [running report](core-planner-p0-report.md) under "Section 10 report: Slices 4 through 10". The text below is historical.

Updated 2026-11-22. Resume **inside Slice 4**, not Slice 5. Slices 4 through 10 are not complete. All changes are uncommitted on the current branch, `full-stack-revamp`.

## User decisions and constraints

- Finish P0 in slice order, using the exact red/green/refactor/full-suite process in section 4.2. Record evidence after each behavior and perform a restored mutation check after each implemented slice.
- Planning must support **all undergraduate majors**. Graduate and professional planning are excluded. The raw program CSV includes other careers because the user requested a complete source export.
- Preserve the entire existing working tree, all tests, untracked root `AGENTS.md`, and `.agents/`. No commits, pushes, branch creation, checkout, reset, merge, cherry-pick or PRs.
- Flask, SQLAlchemy, psycopg and Supabase-hosted PostgreSQL remain. Existing Google authentication and opaque-cookie sessions remain. No Supabase SDK or Supabase Auth migration.
- `.env.example` now includes the user's exact placeholders `SUPABASE_URL=key-something` and `SUPABASE_PUBLISHABLE_KEY=key-something`. They are optional metadata; database connections still use `DATABASE_URL`. No real `.env` or credentials were read or changed.
- Do not edit `backend/data/courses.db`, run startup schema changes, log transcript contents, copy student fixtures, add secrets or add literal em dashes. Migrations are Alembic only. PostgreSQL integration requires an explicitly designated disposable database; none has been supplied.
- Ask if academic facts cannot be sourced, a dependency or breaking API change is not approved, or a real APAS/transcript sample is needed. A real redacted sample has **not** been provided.

## Read first

1. Root `AGENTS.md`, `.claude/AGENTS.md`, `.claude/CLAUDE.md` and applicable skills. Preset skill paths under `.Codex/skills` were missing; installed copies used in this work are under `C:/Users/ijdar/.agents/skills/`, including `concise`, `backend-patterns` and `cleaner`.
2. [P0 spec](specs/core-planner-p0.md), [binding requirements v2 contract](specs/program-requirements-v2.md), [consolidation inventory](specs/branch-consolidation-slice-3-5.md), [running report](core-planner-p0-report.md), and [feature audit](feature-audit.md).
3. [Local setup](running-locally.md), root README and nearest code/tests. Before frontend work also read [design rules](design-rules.md), the frontend technical design and the applicable `simple-design` skill.

## Verified state

- Final full backend run: **212 passed**, with 180 pre-existing migration deprecation warnings. Command from `backend`: `uv run pytest -q`. Cleaner independently verified 208 before finding one optional-name validation gap; four new red/green cases fixed that gap, then the final full suite passed. That small correction was not independently rereviewed.
- Frontend typecheck/build have a known pre-existing TS7006 at `frontend/src/features/auth/GoogleSignInButton.tsx:32`. No frontend work was done in this continuation, so those commands were not rerun here. The earlier report contains the actual failing commands.
- Slices 0 through 2, Slice 3 calculations/API, and the functional Slice 3.5 consolidation checks are implemented. Slice 3 selected-program total lookup still waits for Slice 4.
- The report documents an earlier Slice 3.5 TDD chronology deviation. Do not claim perfect historical process compliance or recreate artificial red states.
- Live branch heads were checked during Slice 3.5 and matched the cached inventory; the nullable-term duplicate constraint was selectively reimplemented with a new forward migration. No branch code was merged or checked out.

## Current Slice 4 code

- `backend/app/services/programs.py`: version-specific file lookup, supported-term listing, `ProgramVersionUnavailable`, and `ProgramVersionUnconfirmed`. Unknown majors return `None`. Data is validated before being returned.
- `backend/app/schemas/programs.py`: strict v2 envelope, real retrieval dates and source records, expression shapes and bounds, grade-policy shapes, globally unique group/rule/adjustment IDs, course-set declarations, sharing declarations, and adjustment effect/stacking/cycle validation.
- `backend/tests/test_programs.py`: 93 passing synthetic loader/validation cases, including the review correction for optional `officialName` types. Original valid fixture remains `backend/tests/fixtures/programs/synthetic--fall-2026.json`.
- Validation is not an evaluator. No coursework qualification, evidence allocation, progress calculation, metadata resolver or scheduling exists yet.
- Mutation check: temporarily disabled `validate_adjustments(program, nodes)`, ran `uv run pytest tests/test_programs.py -q -k dependency_cycles --tb=short`, observed 17 intended `DID NOT RAISE ProgramDataError` failures, then restored exact original bytes in `finally`. Post-restoration review/suite evidence is in the running report.

## Data already available

- [Program snapshot and refresh guide](../backend/data/catalog-exports/README.md): `backend/data/catalog-exports/programs.2026-11-22.csv`, 880 distinct listed Twin Cities programs/revisions. The JSON cells retain native Coursedog rules, alternatives, bounds, notes, admission sections and sub-plan sections.
- Source snapshot is **not** the canonical planner v2 schema. Do not point the v2 loader at the export directory or treat every source row as a supported undergraduate major. Of the 880 rows, 360 are labeled Undergraduate, which also includes minors/certificates. Some source careers/types are blank; do not guess them from names.
- Source selection window `2027-09-07` through `2032-12-15` is the website's published query context, not a catalog term for every program. Each row retains its own effective dates. Computer Science revision `019627107-2026-09-08` is explicitly effective Fall 2026, with 120 degree credits and 78 to 80 program credits.
- Supplied course CSV, read-only: `C:/Users/ijdar/Downloads/courses-report.2026-11-23.csv`. It has 14,156 Twin Cities courses and 13 columns covering names, descriptions, credits, repeatability, grading, requirements and typical offerings. It lacks Coursedog internal IDs and a catalog-term column.
- Native program trees reference internal course IDs. Resolve them to official course codes and matching-version facts. The bundled catalog's version is `unknown`, so it cannot silently override verified supplemental metadata.
- `backend/scripts/export_programs.py` is a separate, tested source exporter. It discovers current catalog settings and public filters, paginates by unique revision ID, rejects changing totals/duplicates/incomplete pages, and refuses empty or existing output files. It uses public Origin and `x-requested-with: catalog` headers without login or tokens. `backend/tests/test_program_export.py` has 11 tests.
- Public sources: `https://umtc.catalog.prod.coursedog.com/programs`, `https://umtc.catalog.prod.coursedog.com/courses`, and `https://schedulebuilder.umn.edu/`. Schedule Builder exposes term-specific pages such as `/explore/2026Fall/PHYS/1301W/`. No user token is needed for those public pages.

## Remaining work, in order

### Finish Slice 4

1. Complete schema tests and implementation for `courseMetadata`, prerequisite-expression records, `catalogCompatibility`, and required course-title/credit coverage. Unknown prerequisites must remain distinct from sourced, verified-empty prerequisites.
2. Add positive acceptance coverage for all valid expression types, sourced sharing and adjustments, and remaining malformed group/policy shapes. Current tests heavily cover rejection paths. Keep existing assertions intact.
3. Add in-memory caching keyed by program/version with testable clearing and independent directory handling. Reject ambiguous duplicate name/version registrations rather than silently selecting conflicting files. Decide and test how malformed unrelated seed files affect lookups.
4. Implement the pure requirement evaluator: completed versus projected evidence, nested whole alternatives, credit/count limits, shared allocation pools and caps, non-transitive top-level sharing, grade thresholds, best qualifying repeated attempts, sourced one-time adjustments and review propagation. Credit totals alone must never certify degree completion.
5. Implement version-aware catalog/supplement resolution. Test compatible precedence, target-version overrides, verified-source conflicts, supplemental-only courses and unknown offering/prerequisite warnings. No catalog SQLite writes.
6. Map official undergraduate program source data to sourced v2 files. Preserve complete alternatives and exceptions; keep advisor-only obligations explicit as review states. Start with the required Fall 2026 Computer Science acceptance case, then extend verified mapping to all undergraduate majors without inventing semantics. Preserve profile-name compatibility and official names.
7. Correct the second-version synthetic test fixture when strict metadata-term validation is added: it currently changes the program term to Fall 2027 but copies metadata still labeled Fall 2026. Make the synthetic metadata legitimately belong to the second version; do not weaken version-isolation assertions.
8. Add a **new** nullable `plans.catalog_term` migration after `e4b7c2a91d06`, plus model field and empty/populated upgrade, downgrade and drift tests. Preserve earlier migrations.
9. Integrate selected-program totals into `/summary`, proving a synthetic non-120 total and retaining existing math/ownership tests. No version confirmation must silently apply a candidate year.
10. Run the full suite, restored mutation check and cleaner review. Update the data format/source documentation and running report before moving on.

### Slice 5: planning engine

Implement pure term helpers, full prerequisite-tree evaluation, eligibility, deterministic requirement-aware alternative selection, prerequisite closure, bounded Fall/Spring placement and whole-plan validation. Try another complete branch when the first is infeasible. Respect load, offerings, sharing and adjustments; emit honest partial/review warnings. Use the exact synthetic acceptance cases in the spec.

### Slice 6: plan API

Add owner-filtered plan repository/service and GET/PUT routes. Return confirmed-version metadata and completed/projected progress. Support catalog-only and supplemental-only additions. Reject invalid batches atomically with documented violations. Preserve saved edits and version selections, and test two-user isolation.

### Slice 7: generation API and full API flow

Add synchronous generation, dry-run parity/no writes, generated persistence and ownership. Preserve distinct unsupported/unconfirmed/unknown-program responses. Add sign-in through coursework, generate, summary, plan edit and fresh-client reload flow test. Do not mark onboarding complete for an unconfirmed version.

### Slice 8: transcripts

Request a real redacted APAS/transcript sample before validating real parser assumptions. No sample exists yet. Approved dependencies are `pdfplumber` and a small dev PDF generator such as `reportlab`. Implement the synthetic parser/PDF boundary and synchronous upload/status/OCR-unavailable APIs with size/signature checks, sanitized filenames, atomic replacement, provenance, auth/Origin/ownership, no retained PDF/raw text, no sensitive logs, and no database session held across parsing.

### Slice 9: frontend wiring

Add the approved Vitest/jsdom/Testing Library/user-event/jest-dom/MSW stack. Follow the spec's per-function and component red/green process. Replace P0 mock endpoints, persist/resume onboarding coursework, handle transcript states, call real generation/save, select catalog terms, show completed/projected requirement progress and translated warnings, support catalog-only/supplemental additions, and protect metadata-blocked actions. Honor the user's all-undergraduate-major scope in program selection. Resolve the recorded TS7006 so typecheck/tests/build pass. Keep only explicitly out-of-scope mocks and report why each remains.

### Slice 10: documentation and final verification

Update feature audit status/affected sections without rewriting its original audit header, setup/test/smoke instructions, and program format/source/version guidance. Change root README only where necessary. Complete section 10's six-part final report, separating verified outcomes from pending PostgreSQL, real Google sign-in, real PDF parsing and browser checks.

## Commands and practical notes

From `backend`:

```powershell
uv run pytest -q
uv run pytest tests/test_programs.py -q
uv run pytest tests/test_programs.py -q -k <behavior> --tb=short
```

From `frontend`, PowerShell execution policy blocks `npm.ps1`; use:

```powershell
npm.cmd run typecheck
npm.cmd test
npm.cmd run build
```

`npm.cmd test` is only available after Slice 9 adds it. Sandbox invocations of uv often cannot access its existing cache; prior authorized test runs used escalation. Never fall back to the real database to work around test setup. Tests already create migration-backed disposable SQLite files.

Suggested next-agent instruction: "Continue Gopher Planner P0 from the unfinished Slice 4 described in docs/core-planner-p0-handoff.md. Read the binding guidance, full P0/v2 specs and report first. Support all undergraduate majors, preserve the current working tree and every test, follow one-behavior TDD plus full-suite and mutation checks, and continue through Slice 10 unless an explicit stop condition applies. Do not claim the raw CSV is validated planner data."
