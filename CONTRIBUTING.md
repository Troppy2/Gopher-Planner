# Contributing to Gopher Planner

Contributions can be code, documentation, accessibility fixes, synthetic test cases, or corrections backed by official academic sources. Read the [Code of Conduct](CODE_OF_CONDUCT.md), [project guide](docs/PROJECT.md), and [architecture](docs/ARCHITECTURE.md) before making a substantial change.

## Pick a focused change

Check [existing issues](https://github.com/Troppy2/Gopher-Planner/issues) and the [roadmap](docs/ROADMAP.md) first. An open issue may already be partly implemented. Read the relevant source and describe the remaining gap instead of rebuilding from an old checklist.

For a bug, include the screen/API route, triggering action, expected and actual behavior, browser/OS, and a minimal synthetic reproduction. Include the selected catalog year for planning problems. Add a redacted screenshot only when it helps explain the issue.

Discuss large features, data sources, schema changes, or new dependencies in an issue before starting. Small documentation fixes and reproducible bug fixes can go straight to a focused pull request. Report vulnerabilities privately using [SECURITY.md](SECURITY.md).

## Development workflow

Use the [feature implementation checklist](docs/IMPLEMENTING_FEATURES.md) to trace a change from design through storage, API, UI, migrations, and verification. It includes an optional spec outline.

1. Follow the [quick start](README.md#quick-start). Keep credentials local and use a development database.
2. Work from a fork or a branch agreed with the maintainers.
3. Read `AGENTS.md` and relevant module documentation for project conventions. If a local `.claude/CLAUDE.md` is present, read it too; that ignored file is not part of a fresh clone.
4. Add a failing regression test for behavior changes, then implement the smallest complete fix.
5. Exercise the important failure path, ownership boundary, or scheduling constraint. A quick mutation check should prove the new assertion detects a broken condition.
6. Update docs when setup, behavior, APIs, source provenance, or limitations change.
7. Keep unrelated formatting, generated data, and dependency upgrades out of the PR.

Use the existing lockfiles: `uv sync` and `npm ci`. Do not add another package manager or a dependency for a problem the current stack already solves.

## Frontend conventions

- Read [docs/design-rules.md](docs/design-rules.md) before UI work.
- Reuse `frontend/src/ui/` components and maroon, gold, and ivory tokens.
- Keep server data in TanStack Query, navigation/filter state in the URL where appropriate, and temporary drafts in their existing stores.
- Preserve input and existing content during background requests. Cover initial loading, empty, error, retry, disabled, and success states.
- Verify keyboard operation, accessible names, focus restoration, mobile layouts, and scrolling around drawers and menus.
- Use layout-matched skeletons for unavailable data. Do not show fake zeroes or empty lists before a request completes.

## Backend conventions

- Keep HTTP handling in routes, business behavior in services, and owner-filtered persistence in repositories where those boundaries exist.
- Derive identity from the authenticated session. A client-supplied user ID is not authorization.
- Validate inputs and ownership at route and service boundaries.
- Change schema only through Alembic. Do not create or alter tables from the app factory.
- Keep OCR, generation, and external calls outside long-lived database transactions.
- Preserve per-user write locks and snapshot checks around plan/coursework replacement.
- Never log transcript text, grades, credentials, or student data.

## Academic data changes

Accuracy requires evidence. Do not infer requirements, prerequisites, LE designations, substitutions, or degree equivalences from names.

- Identify the official source, program, and catalog version.
- If a fact is absent from the repository's sourced data, ask the maintainers before encoding it.
- Keep machine-mapped programs unverified until reviewed. Do not turn a warning into a hard prerequisite check without evidence.
- Follow [the data guide](backend/data/README.md) and [v2 requirement contract](docs/specs/program-requirements-v2.md).
- Never edit `backend/data/courses.db`; it is a read-only import source.
- Build candidate files in a scratch directory and review differences before replacing shipped data.
- Describe source coverage, unmatched records, and unresolved review items in the PR.

External integrations need an agreed source, terms, rate limits, storage plan, and failure behavior. Do not introduce authenticated university-account automation or a scheduled scraper without that discussion.

## Privacy and fixtures

Use only synthetic coursework, invented identities, and generated PDFs. Do not use real APAS reports to reproduce parser bugs. Build a synthetic document with the same structural problem instead.

Do not commit `.env` files, user databases, raw uploads, cookies, student screenshots, OCR dumps, or sensitive debug logs. Check staged files before submitting.

## Verification

From `backend`:

```powershell
uv run pytest -q
```

From `frontend`:

```powershell
npx.cmd vitest run --maxWorkers=1
npx.cmd tsc -b --noEmit
npm run build
```

Use `npx` on macOS/Linux. Run focused checks during development and the relevant full suite before review. For documentation-only changes, check links, paths, commands, and claims against source; a full application test run is not required unless behavior changed.

Backend tests use disposable SQLite databases by default. PostgreSQL tests need a disposable local database through `TEST_DATABASE_URL`; fixtures drop and recreate its public schema. Never use Supabase, production, or a shared database.

For migrations, verify upgrade from the previous revision with existing synthetic rows, and review downgrade behavior. Do not apply schema changes or catalog imports to a shared database as routine PR verification.

For UI changes, check desktop and narrow mobile viewports. For planner changes, cover duplicates, prerequisite order, load limits, dry-run persistence, and ownership where relevant. Report anything not verified.

## Pull requests

- Explain the user-visible problem and resulting behavior.
- Link the issue and identify the acceptance criteria this PR actually satisfies.
- List tests run and results; include synthetic screenshots for material UI changes.
- Explain migrations, data-source changes, and deployment implications.
- Keep limitations visible in the product and documentation.
- Confirm no private records, credentials, or unintended artifacts are included.

Avoid closing a broad issue because one part is complete. Suggest follow-up work explicitly. Maintainers may request smaller changes or additional evidence before merging. Participation follows the [Code of Conduct](CODE_OF_CONDUCT.md).
