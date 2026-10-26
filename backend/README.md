# Backend

Flask REST API for Gopher Planner. Uses SQLAlchemy, Alembic, PostgreSQL (user data), SQLite (course catalog seed data), and `pdfplumber` for transcript parsing.

Layering: `api` (HTTP) -> `services` (business logic) -> `repositories` (DB access) -> `models`.
Rules: verify ownership at route and service boundaries, never log transcript contents, never hold DB sessions across slow external calls, never change schema at startup (use Alembic).

## Current scope

The infrastructure provides an application factory, PostgreSQL configuration,
a read-only database check, and Alembic migrations. Stage 3 step 1 adds only
`student_profiles`, `course_records` and `extra_credits` storage models and their
migration. Stage 3 step 2 adds the opt-in local development academic snapshot
GET/PUT API. Authentication, parser, catalog loading and planning remain absent.
`GET /api/v1/health` is application liveness only; it does not test PostgreSQL.
SQLite is reserved for the separate course catalog, never student data.

## Install (macOS / zsh)

```sh
cd /Users/sylvial/Documents/GopherPlanner/Gopher-Planner/backend
python3 -m venv .venv                 # only if .venv does not already exist
source .venv/bin/activate
python -m pip install -r requirements.lock
```

`requirements.txt` lists direct dependency ranges; `requirements.lock` records
the exact installed versions tested on Python 3.12, including pytest.

## Local PostgreSQL initialization

Use an existing PostgreSQL 15+ database if available. Otherwise, with Docker
Desktop running, the following creates a dedicated development PostgreSQL 16
container and persistent volume. Stage 2 database acceptance has now created
these resources; do not run the creation command again on this machine. Check
for an existing container/volume with these names before use;
do not overwrite or delete existing resources.

```sh
docker ps -a --filter name=gopher-planner-postgres
docker volume ls --filter name=gopher-planner-pgdata
# Enter a new local password; it is not stored in shell command history.
read -rs 'POSTGRES_PASSWORD?Local PostgreSQL password: '
export POSTGRES_PASSWORD
docker run --name gopher-planner-postgres \
  --env POSTGRES_USER=gopher \
  --env POSTGRES_PASSWORD \
  --env POSTGRES_DB=gopher_planner \
  --publish 127.0.0.1:5432:5432 \
  --volume gopher-planner-pgdata:/var/lib/postgresql/data \
  --detach postgres:16
unset POSTGRES_PASSWORD
docker exec gopher-planner-postgres pg_isready -U gopher -d gopher_planner
```

For an existing stopped development container, use
`docker start gopher-planner-postgres` instead of another `docker run`.
If port 5432 is occupied, choose a different host port and update the URL below.
The volume preserves the database across container restarts. Do not delete it
to fix connection problems. Initialization environment variables only apply to
a new database volume.

## Configuration

Copy `.env.example` to `.env` only if `.env` does not already exist. Edit `.env`
locally: set `DATABASE_URL` to
`postgresql+psycopg://gopher:YOUR_URL_ENCODED_PASSWORD@127.0.0.1:5432/gopher_planner`
using the password entered above. URL-encode password characters such as `@`,
`/`, `:` and `%`. Do not commit or share the actual password.

`load_settings()` reads `backend/.env`; exported environment variables take
priority. Missing URLs, SQLite URLs and a driver other than `postgresql+psycopg`
are rejected. The URL is not copied into public Flask configuration or printed
by the database-check command.

`ENABLE_DEV_STUDENT_API` defaults to `false`. Only the exact strings `true` and
`false` are accepted. Enabling it requires `APP_ENV=development`. The application
registers the student API only when explicitly enabled in development. The
switch is not authentication; it must not be enabled for a public deployment.

## Check, migrate and start

From `backend`, with the virtual environment active and `.env` configured:

```sh
python -m flask --app app:create_app check-db
python -m alembic upgrade head
python -m alembic current
python -m flask --app app:create_app run --host 127.0.0.1 --port 5000
```

If port 5000 is occupied, use `--port 5051`. In another terminal:

```sh
curl --noproxy '*' http://127.0.0.1:5000/api/v1/health
```

Expected response: `{"status":"ok"}`. Stop Flask with Ctrl+C.
Starting Flask configures a lazy connection engine; it neither connects to
PostgreSQL nor creates tables. Therefore HTTP success alone does not establish
database readiness. `check-db` performs `SELECT 1` and checks PostgreSQL >= 15.

Migration means an explicit database structure update. Alembic is already
initialized; do not run `alembic init` again. `0001_baseline` has no academic
table operations. Applying it creates only Alembic's revision bookkeeping table.
`0002_academic` explicitly creates the three academic tables. No startup code
calls `create_all()` or runs Alembic.

## Tests and stage 2 verification

```sh
python -m pytest -q
python -m pip check
python -m alembic heads
python -m alembic upgrade head --sql
```

Tests cover configuration rejection, startup without a database, liveness,
the development switch and sanitized connection errors. They do not substitute
SQLite, an in-memory database or mocks for PostgreSQL acceptance. Offline SQL
generation does not apply a migration or verify a PostgreSQL connection.

Initial infrastructure checks: 9 pytest cases passed, `pip check` passed,
Alembic reported `0001_baseline` as its head, and offline upgrade SQL was
generated. A temporary Flask process bound to `127.0.0.1:5051` returned HTTP 200
with `{"status":"ok"}` and was then stopped. PostgreSQL was initially unavailable.

Stage 2 database acceptance (2026-10-12): after verifying that the container,
named volume and local `.env` did not exist and port 5432 was available, created
`gopher-planner-postgres` using `postgres:16` with the dedicated named volume
`gopher-planner-pgdata`. Verified binding only to `127.0.0.1:5432`. A random local
password is stored only in local configuration and the container environment;
`.env` has mode 0600 and is ignored by Git. The development student API stays off.

Actually executed `flask --app app:create_app check-db`, `alembic upgrade head`,
and `alembic current`: all succeeded. The server reported PostgreSQL 16.15 and
current revision `0001_baseline (head)`. A read-only table query confirmed that
`public` contains only `alembic_version`; no academic tables or student APIs were
created. The container remains running. The volume is configured to retain data;
container restart persistence has not been separately tested in this stage.

## Academic models (stage 3, step 1)

Read `app/models/academic.py` for current ORM classes and constraints, and
`migrations/versions/0002_academic_create_academic_records.py` for the reviewed,
autogenerated schema upgrade. Importing models registers metadata only.
`program` and `catalog_year` accept nonempty trimmed labels, not only the test
sample. Catalog year is a requirement-version label, not a course term.

Terms are stored as year/season columns. Seasons are Spring, Summer and Fall;
years range from 1 to 9999. Current/target terms are required and target must not
precede current. Course terms must be entirely present or entirely absent.
Only completed IB/AP/transfer records can have an unknown term. Institutional
records need a term; an in-progress row must be institutional, with zero earned
credits and no final grade. Credits use NUMERIC(6,2); earned credits cannot exceed
course credits. NaN is rejected by bounded credit checks.

Grade supports A, A-, B+, B, B-, C+, C, C-, D+, D, F, S, N or NULL. Grading basis
is AF, SN or NULL, independent from final grade. Known AF/SN and grades must be
compatible; F/N requires zero earned credits. IB/AP mapped credit has no grade
or grading basis. Unsupported W/I/T5/T6 are rejected, not interpreted.
Unknown grades do not imply passing or failing or meeting a minimum grade.
Sources are institutional, IB, AP or transfer.

The database enforces:

- Child `student_id` foreign keys (CASCADE on explicit parent deletion), required
  fields, value ranges and the row-local combinations above.
- `UNIQUE NULLS NOT DISTINCT (student_id, course_code, term_year, term_season)`:
  the same course can occur in different terms, but not twice in the same term
  or twice with an unknown term, regardless of source/status.
- Unique non-NULL course credit-reference per student and unique extra-credit
  reference per student. A course credit-reference identifies one allocation,
  not an entire IB exam; one exam may map to several different course records.
- Extra usage is either false/NULL or true/nonempty text. It records a person's
  confirmation of purpose, not a verified graduation rule or deduplication check.

The API/service now enforces full snapshots, fixed student identity, input
shapes/precision, in-progress term equality to current term, completed term not
after current, and matching references across the two credit tables in one
transaction. Program/catalog labels are stored without claiming any official
requirement support; supported planning scope belongs to the future rule engine.
No cross-table trigger or extra identity system was added. PostgreSQL NUMERIC
can round excessive input precision; the API rejects it before insertion.
Missing/different references cannot prove two credits are distinct; those cases
need human review. Retakes are preserved, not summed as valid graduation credit.

For opt-in real PostgreSQL tests (only this local development database):

```sh
RUN_POSTGRES_MODEL_TESTS=true python -m pytest tests/test_academic_postgres.py -q
```

All test data is fictional; each test rolls back its database transaction.
On 2026-10-12, applied `0002_academic`, verified all three tables, both foreign
keys, all three unique constraints and required columns using PostgreSQL schema
inspection. `alembic current` reported `0002_academic (head)`; `alembic check`
reported no new upgrade operations. 26 real PostgreSQL model checks and the
9 infrastructure checks passed. All three academic tables had zero rows after
verification. No student API or frontend changes were implemented.

## Local development academic snapshot API (stage 3, step 2)

`GET /api/v1/dev/student/academic-profile` reads internal student 1. First read
returns JSON 404 until a profile has been saved. `PUT` on the same path saves a
complete snapshot and returns JSON 200 for both creation and replacement. No
client identity parameter or internal record ID is accepted. Query parameters
are rejected. The existing frontend mock `updateProfile(Partial<Profile>)` is
unchanged and is not wired to these routes.

Routes are absent by default. Registration requires both `APP_ENV=development`
and `ENABLE_DEV_STUDENT_API=true`; other environments reject an enabled flag.
For explicit local manual use, bind only to localhost:

```sh
ENABLE_DEV_STUDENT_API=true python -m flask --app app:create_app run --host 127.0.0.1 --port 5000
```

The request shape is demonstrated by `tests/fixtures/academic_profile.json`,
which contains only fictional data. PUT requires `profile`, `course_records`
and `extra_credits`. Both arrays are entire lists; empty arrays clear them, and
omitted old children are deleted. All listed fields must be present, including
nullable grade/basis/term fields. The one exception is optional
`credit_reference`: omission explicitly means an unknown allocation identifier
and is returned as null. Extra fields, partial updates and guessed grades are
not accepted. Validation never trims, changes case, rounds input credit amounts,
or infers grades/terms. Grade null remains unknown. Course codes use canonical
uppercase subject + space + four digits, optionally a final uppercase letter.
Program and catalog year are nonempty labels, not restricted to the fixture.

PUT validates the entire request before opening the database transaction. The
repository upserts/locks student 1, deletes its old children, and inserts the new
children; all operations commit together or roll back together. Duplicate saves
do not append. Response arrays use stable ordering (courses by code and term,
extra credits by reference); array order is not an academic property. Internal
child IDs can change on replacement and are not exposed. GET takes a shared
parent lock, keeping its parent and child queries coherent with API writers.

Only matching known allocation identifiers can detect cross-table duplicate
credit; missing/different identifiers still require human review. One IB exam
can map to different courses; identifiers refer to separate allocations, not
an entire exam. The API computes no GPA, graduation status or total credits,
and applies no repeat-course credit rules.

Responses use `{"error":{"code":"...","message":"...","details":[...]}}`;
`details` is included for field validation failures. Statuses: 404 absent profile,
422 invalid snapshot/identity/constraint, 400 malformed JSON or repeated JSON
keys, 415 non-JSON content type, 413 body over 1 MiB, 503 database failure. All
snapshot responses disable caching. No request bodies or database exception
contents are logged by these routes.

### Independent PostgreSQL acceptance

Run from backend with the virtual environment active:

```sh
python scripts/verify_dev_student_api.py
RUN_POSTGRES_API_TESTS=true python -m pytest tests/test_academic_api_postgres.py -q
python -m pytest tests/test_bootstrap.py tests/test_academic_schema.py -q
```

The acceptance script creates a new unique `gopher_api_test_*` database on the
local server, applies migrations, starts Flask once bound to localhost, tests
real HTTP requests, and stops Flask. It refuses to overwrite an existing
`.env.api-test`. That ignored file has permission 0600 and contains test database
configuration; never share or commit it. The separate test database and final
fictional sample are retained for the following restart-persistence step. The
script does not clear/write the development database and checks that its rows
remain unchanged. Do not delete or overwrite these artifacts to rerun tests.
The additional API pytest tests use only this separate database and roll back
all their fixture transactions.

Actual acceptance on 2026-10-12 used `gopher_api_test_a60848659264`: initial GET
404, PUT 200, identical GET, repeat PUT counts 1/3/1, invalid PUT 422 with the
old entire snapshot unchanged, full child replacement, cross-table reference
rejection, identity rejection and malformed JSON rejection all passed. Eight
additional PostgreSQL API tests passed, including an injected database write
failure after parent/course replacement that returned 503 and restored the old
snapshot. Forty configuration/schema unit tests passed. Development student
API remains disabled in `.env`; only test configuration enables it. Process
restart persistence and frontend integration have not been verified.
