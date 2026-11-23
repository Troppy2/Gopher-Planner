# PostgreSQL verification

**Date:** 2026-11-23
**Revision checked:** `2f0e34a` on `main`
**Database:** PostgreSQL 16.15, a disposable local cluster created for this check only. No Supabase, shared, or production database was used.

Until now every migration and test had only run on SQLite. This records a run against real PostgreSQL so the "PostgreSQL migrations unverified" note in earlier reports can be retired for local PostgreSQL. Supabase-specific behavior is listed separately under "Not covered".

## 1. Full backend test suite on PostgreSQL

From `backend`, with a disposable database (see [running locally](running-locally.md) for the Docker command):

```
TEST_DATABASE_URL=postgresql+psycopg://gp@localhost:55432/gp_test uv run pytest -q -rs
```

Result:

```
SKIPPED [1] tests/test_migrations.py:37: SQLite-specific behavior
525 passed, 1 skipped, 388 warnings in 38.67s
```

The PostgreSQL-only tests (`tests/test_catalog_store.py:119`, `tests/test_migrations.py:120`) ran and passed. The one skip is the SQLite-only migration test, which is expected. On SQLite the same revision gives 524 passed and 2 skipped (the two PostgreSQL-only tests).

## 2. Migrations on an empty database

With `DATABASE_URL` pointing at a fresh empty database:

| Command | Result |
| --- | --- |
| `uv run flask --app app db upgrade` | Applied every revision through head `a1d4e7f93c20`. |
| `uv run flask --app app db check` | `No new upgrade operations detected.` The models and migrations match. |
| `uv run flask --app app db downgrade base` | Every downgrade ran. Only `alembic_version` remained (1 table). |
| `uv run flask --app app db upgrade` | Re-upgrade to `a1d4e7f93c20 (head)` succeeded. |

Row level security from `c8d2a6f19e47` is enabled on all 10 public tables after upgrade (checked with `pg_class.relrowsecurity`).

## 3. Real catalog import

```
uv run python scripts/import_catalog.py --csv data/catalog-exports/courses.2026-11-23.csv
```

Output: `Imported 1 release(s), 25707 courses, 357 prerequisite edges`, in about 2 seconds. The database then held 25,707 courses across 456 subjects, 7,723 with liberal education attributes, and 1 catalog release. Running the same import again left the counts unchanged (still 1 release), so a re-import replaces the catalog rather than duplicating it.

## 4. API flow against the real catalog

A script used the Flask test client with a synthetic signed-in user against the migrated, imported PostgreSQL database:

```
PUT profile: 200 {'major': 'Computer Science B.S.'}
GET courses q=algorithms: 200 {'total': 109}
GET course CSCI 4041: 200 {'code': 'CSCI 4041', 'title': 'Algorithms and Data Structures'}
PUT coursework: 200
POST generate: 200   (plan returned with 237 rows: 26 planned, 210 available alternatives, 1 completed)
GET plan: 200   catalogTerm: Fall 2026
GET summary: 200 {'creditsCompleted': 8.0, 'creditsTotal': 120, 'gpa': 3.83, 'program': 'Computer Science B.S.'}
```

The coursework was two completed courses (A and A-, 4 credits each) and one in-progress course. The summary counts only the 8 completed credits, and the GPA is (4.0 + 3.67) / 2 = 3.83, as expected. Case-insensitive search (`ilike`) works on PostgreSQL.

## Not covered

- **Supabase itself.** Roles, the session pooler, `sslmode=require`, and the Data API were not exercised. Row level security was confirmed enabled but not tested from a Supabase client role.
- Concurrency under real load. The PostgreSQL locking tests pass, but no multi-process load test was run.
- Real Google sign-in, real APAS PDFs, and browser flows, as in earlier reports.
