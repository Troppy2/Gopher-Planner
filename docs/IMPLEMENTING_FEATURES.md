# Implementing a feature

Use this checklist to take a Gopher Planner feature from an idea to a verified pull request. After defining the feature, start with the lowest layer it changes. A UI-only feature can go straight to step 6. An API-only feature can skip the frontend steps.

## 1. Define the feature

- [ ] Read the relevant issue and trace the existing behavior through the code. An open issue may already have some of the work implemented.
- [ ] Write down who needs the feature, what they can do when it is finished, and how you will verify it. Note what is out of scope and any decisions that still need an answer.
- [ ] Consider a spec in `docs/specs/<feature-name>.md`. A spec is helpful when a change spans the database, API, and UI, or changes academic rules. For a small feature, a description and acceptance criteria in the issue or PR are enough.
- [ ] Add a failing regression test for changed behavior. Use synthetic coursework, accounts, and generated PDFs. Ground academic rules in the project's official source data and ask a maintainer if the needed fact is missing.

An optional spec can use this outline:

```markdown
# Feature name

## Problem and user outcome
## Scope and open decisions
## Data, API, and ownership
## UX and failure states
## Acceptance criteria and verification
```

## 2. Decide whether storage changes

- [ ] Check whether the feature can use existing records or derive the new value from data already available. Identify which data is user-owned, catalog data, program JSON, or browser-only state.
- [ ] If persistent storage changes, update the SQLAlchemy models in `backend/app/models/`. Import new models in `backend/app/models/__init__.py` so Alembic sees them. Check keys, nullability, defaults, and how existing rows will behave.
- [ ] Update related queries in `backend/app/repositories/` and the logic that uses them in `backend/app/services/`. Filter user-owned queries by the authenticated owner and keep related writes in one transaction. Keep slow work such as OCR and external calls outside that transaction.
- [ ] Record the migration needed for step 7. Make schema changes through Alembic and keep `backend/data/courses.db` read-only.

## 3. Implement the service and API contract

- [ ] Put business rules in the service or existing domain module. Keep request parsing, response formatting, and HTTP status handling in the route. Define or extend validation in `backend/app/schemas/` where it fits.
- [ ] Decide whether to extend an existing `/api/v1` route or add a new one in `backend/app/api/v1/`. Register a new blueprint in `backend/app/__init__.py` if needed. Routes should call services for business behavior and use models or repositories through the existing persistence boundaries.
- [ ] Verify authentication and ownership on protected operations, including the origin check for writes. Check how existing callers handle new or missing fields, errors, and empty responses.
- [ ] Cover the service and API behavior with tests for successful requests and relevant failure cases, such as invalid input, a second user's records, or a write that must roll back.

## 4. Add the frontend API binding

- [ ] Define the request and response shapes in `frontend/src/api/types.ts`. Add or extend the function in `frontend/src/api/endpoints.ts` using the shared API client where applicable.
- [ ] Reuse or add query keys in `frontend/src/api/queryKeys.ts`. Think through which cached data a write affects. A coursework edit, for example, can change both the plan and dashboard summary.
- [ ] Update the synthetic MSW handlers in the relevant frontend tests to match the backend contract.

## 5. Wire the binding into the feature

- [ ] Call the endpoint from the owning screen or feature hook. Use TanStack Query for server data and mutations. Keep temporary UI input and plan drafts in their existing state boundaries.
- [ ] Connect the query or mutation to the normal entry point, such as a course drawer, settings form, or planner action. Refresh affected queries after a save and preserve user input if it fails.

## 6. Build the UX

- [ ] Read the design rules before UI work. Reuse the controls in `frontend/src/ui/` and existing page layouts. [Design rules](design-rules.md)
- [ ] Design the usable, loading, empty, error, and saving states that apply. Match skeletons to the loaded layout and keep existing content visible during background requests where possible.
- [ ] Check keyboard operation, focus, readable errors, narrow mobile layout, and the complete flow from action to saved result.

## 7. Generate, review, and apply the migration locally

Use this step when the schema changes. The commands run from `backend` against a dedicated local development database. Configure `DATABASE_URL` for that local database before running them and verify the target without printing credentials. Keep `TEST_DATABASE_URL` separate and use it only for a disposable local PostgreSQL test database. The test fixtures drop and recreate its public schema.

1. Bring the local database to the **existing** head before adding the new revision. If the database already has pending revisions from other work, apply those first so autogeneration compares your models to the right baseline.

   ```powershell
   uv run flask --app app db current
   uv run flask --app app db heads
   uv run flask --app app db upgrade
   ```

2. After updating and importing the models, generate the revision. This writes a migration file and leaves schema application to `db upgrade`. For a data migration that autogeneration cannot express, use `uv run flask --app app db revision -m "describe data change"` and write the operations explicitly.

   ```powershell
   uv run flask --app app db migrate -m "describe schema change"
   ```

3. Review the generated file in `backend/migrations/versions/`. Check `down_revision`, table and column operations, constraints, indexes, defaults, and both `upgrade()` and `downgrade()`. Check renames and backfills explicitly. For example, populate existing rows before making a new column required. Remove unrelated changes generated by schema drift.

4. Apply the reviewed revision locally, then confirm the database revision matches the intended head. Run this before manually testing any code that reads or writes the new schema.

   ```powershell
   uv run flask --app app db upgrade
   uv run flask --app app db current
   ```

5. Verify an upgrade from the previous revision with existing synthetic rows, plus a clean install. Test downgrade and re-upgrade on a disposable copy where the downgrade is supported. Note any data-loss implications in the PR. Include the revision file with the feature. Applying it to a shared database is a separate deployment step.

## 8. Run backend checks

From `backend`:

```powershell
uv run pytest -q
```

Use focused tests during implementation, then run the full backend suite for backend changes. SQLite is the default. For PostgreSQL-specific behavior such as row locking, follow the disposable database setup and report which checks you ran. [Local test setup](running-locally.md#backend-tests)

## 9. Run frontend checks and verify the feature

The frontend currently has Vitest, TypeScript, and a production build command. ESLint has no project configuration or script. From `frontend` on Windows PowerShell:

```powershell
npx.cmd vitest run --maxWorkers=1
npx.cmd tsc -b --noEmit
npm run build
```

Use `npx` on macOS or Linux. For changes spanning both layers, run both suites and smoke-test the actual screen against the local API with synthetic data. Check the result after reload if it should persist.

## Ready for review

- [ ] Acceptance criteria are verified through the feature's normal entry point.
- [ ] Relevant tests pass and catch the behavior they cover. For changed logic, briefly break the relevant condition and confirm the regression test fails, then restore it.
- [ ] Schema changes include a reviewed migration and evidence that existing rows upgrade, where applicable.
- [ ] Docs and wire types reflect the resulting behavior. The PR records the issue or optional spec, commands and results, and anything still unverified.
- [ ] The change contains only synthetic fixtures and no secrets or student records. [Pull request template](../.github/PULL_REQUEST_TEMPLATE.md)
