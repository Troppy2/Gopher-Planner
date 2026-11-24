# Running Gopher Planner Locally

This guide covers running the React frontend and Flask backend on your machine.

Shared deployments use PostgreSQL for user data and the runtime course catalog; Supabase is one supported hosting destination. Local development can use PostgreSQL or the SQLite fallback. After migrating your intended local database, load catalog data with `uv run python scripts/import_catalog.py --csv data/catalog-exports/courses.2026-11-23.csv`. This command replaces catalog seed tables. Flask uses SQLAlchemy, Alembic migrations, Google credential verification, and opaque cookie sessions. See the [README](../README.md#quick-start) for the shortest local setup and [architecture](ARCHITECTURE.md) for deployment limits.

## Ports

| Service | URL | Notes |
| --- | --- | --- |
| Frontend (development) | http://localhost:5173 | Vite dev server |
| Frontend (Docker) | http://localhost:3000 | nginx serving the production build |
| Backend API | http://localhost:5000 | Flask, health check at `/health` |
| PostgreSQL | localhost:5432 | Only needed when using PostgreSQL |

## Prerequisites

- Node.js 22.12 or newer and npm
- Python 3.12 or newer
- [uv](https://docs.astral.sh/uv/getting-started/installation/) for the backend
- Docker Desktop if you want to run PostgreSQL or the full stack in containers
- A Google OAuth client ID (see `VITE_GOOGLE_CLIENT_ID` below)

## Agent prompt: run the app locally

For coding agents, start in the repository root and use the command block for the agent's host OS. Preserve the selected database target, do not print secrets, and stop before any migration or catalog import if the intended database is not explicitly local or disposable.

### macOS or Linux

```bash
cp .env.example .env
cp backend/.env.example backend/.env
cp frontend/.env.example frontend/.env

cd backend
uv sync
uv run flask --app app db upgrade
uv run flask --app app run --debug --port 5000
```

In a second terminal:

```bash
cd frontend
npm ci
npm run dev -- --port 5173 --strictPort
```

Activate a plain Python virtual environment instead of `uv` with:

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -e .
flask --app app db upgrade
flask --app app run --debug --port 5000
```

### Windows PowerShell

```powershell
Copy-Item .env.example .env
Copy-Item backend/.env.example backend/.env
Copy-Item frontend/.env.example frontend/.env

cd backend
uv sync
uv run flask --app app db upgrade
uv run flask --app app run --debug --port 5000
```

In a second PowerShell terminal:

```powershell
cd frontend
npm ci
npm run dev -- --port 5173 --strictPort
```

Activate a plain virtual environment instead of `uv` with:

```powershell
cd backend
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -e .
flask --app app db upgrade
flask --app app run --debug --port 5000
```

Open http://localhost:5173. The frontend proxies `/api` to the backend on port 5000. For SQLite, leave `DATABASE_URL` empty in development; otherwise run and verify PostgreSQL before starting the backend.

## 1. Environment variables
Configuration templates are committed; actual credentials are not. The backend reads existing process variables first, then `backend/.env`, then root `.env`. Docker Compose uses root `.env`. A value in `backend/.env` takes precedence over the same value in root `.env`, so keep the intended development target explicit.

From the repository root:

```powershell
Copy-Item .env.example .env
```

Then edit `.env` and set at least:

```env
POSTGRES_DB=gopher_planner
POSTGRES_USER=gopher_planner
POSTGRES_PASSWORD=your_local_database_password

DATABASE_URL=postgresql+psycopg://gopher_planner:your_local_database_password@localhost:5432/gopher_planner

GOOGLE_CLIENT_ID=your-client-id.apps.googleusercontent.com
FRONTEND_ORIGIN=http://localhost:5173
JWT_SECRET=a_long_random_string
COOKIE_SECURE=false

VITE_GOOGLE_CLIENT_ID=your-client-id.apps.googleusercontent.com
```

Notes:

- `GOOGLE_CLIENT_ID` and `JWT_SECRET` are required. The backend refuses to start without them.
- `FRONTEND_ORIGIN` must match the URL you open the frontend at. Use `http://localhost:5173` for the dev server, or `http://localhost:3000` for the Docker frontend.
- In development, `DATABASE_URL` is optional. If it is empty, the backend creates a SQLite database at `backend/instance/dev.db`. If it is set, PostgreSQL must be running.
- `VITE_GOOGLE_CLIENT_ID` must be the same OAuth client ID as `GOOGLE_CLIENT_ID`.
- Never commit `.env` or real secrets.

The frontend also reads `frontend/.env` for Vite variables:

```powershell
Copy-Item frontend/.env.example frontend/.env
```

```env
VITE_GOOGLE_CLIENT_ID=your-client-id.apps.googleusercontent.com
```

Do not set `VITE_API_URL` for normal development. The Vite dev server proxies `/api` requests to `http://localhost:5000`, which keeps cookies same-origin. Most API calls use relative `/api/v1/...` paths.

## 2. Start PostgreSQL

With Docker:

```powershell
docker compose up -d db
```

Or start an existing local PostgreSQL 15+ service and create the database and user that match `DATABASE_URL`.

Check that it is accepting connections:

```powershell
docker compose ps
```

## 3. Run the backend

```powershell
cd backend
uv sync
uv run flask --app app db upgrade
uv run flask --app app run --debug --port 5000
```

- `uv sync` installs dependencies from `pyproject.toml` and `uv.lock`.
- `db upgrade` applies the Alembic migrations. Run it again after pulling schema changes.
- The API reloads on file changes because of `--debug`.

Verify it:

```powershell
Invoke-RestMethod http://localhost:5000/health
```

Expected response: `{"status": "ok"}`.

### Backend without uv

If you prefer a plain virtual environment, install `uv` anyway for the build backend, or install the project into a venv:

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -e .
flask --app app db upgrade
flask --app app run --debug --port 5000
```

On macOS or Linux, activate with `source .venv/bin/activate`.

## 4. Run the frontend

In a second terminal, from the repository root:

```powershell
cd frontend
npm install
npm run dev
```

Open http://localhost:5173.

Useful commands:

```powershell
npm run dev        # development server with hot reload
npm run typecheck  # TypeScript checks only
npm test           # Vitest, jsdom, Testing Library and MSW
npm run build      # typecheck and production build into dist/
npm run preview    # serve the production build on port 5173
```

On Windows PowerShell, if script execution policy blocks `npm`, run `npm.cmd test`, `npm.cmd run typecheck` and `npm.cmd run build` instead.

Coursework, summary, plan, generation and transcripts use the real backend. Only the select options in `getOptions` (standings, graduation targets, subjects, careers) and the Settings preview controls still read `src/api/mock/`; majors come from `GET /api/v1/programs`.

## Backend tests

From `backend`:

```powershell
uv run pytest -q
```

Tests apply the Alembic migrations to a throwaway database, import a small synthetic catalog and use synthetic program files. They never write `backend/data/courses.db`, the shipped program files or Supabase.

By default they use SQLite. To run them on PostgreSQL (needed for the locking tests), start a disposable container and point `TEST_DATABASE_URL` at it. Every test drops and recreates its `public` schema, so never point it at Supabase or any database you care about:

```powershell
docker run -d --name gopher-test-pg -e POSTGRES_USER=gp -e POSTGRES_PASSWORD=synthetic -e POSTGRES_DB=gp_test -p 55432:5432 postgres:17-alpine
$env:TEST_DATABASE_URL = "postgresql+psycopg://gp:synthetic@localhost:55432/gp_test"
uv run pytest -q
```

Optional backend data overrides:

| Variable | Default | Purpose |
| --- | --- | --- |
| `PROGRAM_DATA_PATH` | `backend/data/programs` | Directory of versioned v2 program requirement files. |

## Manual smoke test

1. Sign in with an eligible University of Minnesota Google account.
2. On the coursework step, upload an APAS PDF or enter courses manually (or skip), then continue. Refresh and go back: entries return from the server.
3. On the profile step choose a major from the list, for example `Computer Science B.S.`, plus credit load and graduation target.
4. On the building screen choose the catalog year (Fall 2026 for Computer Science) and build. The plan is saved and onboarding completes.
5. On the dashboard, check credit progress, completed versus planned requirement status and any warnings.
6. In the flow chart, press Build for a dry-run draft and choose Keep this plan after reviewing it. Add a catalog course or move a class; ordinary edits autosave. Try moving a prerequisite after its dependent to see the validation feedback.
7. Reload the page: the plan, catalog year and summary persist.

Automated test results do not establish that a deployed OAuth client, shared database, proxy, or browser/device combination is configured correctly. PostgreSQL-specific tests require their own disposable database. Real APAS/transcript PDFs are excluded from test fixtures; use synthetic documents for parser verification.

## 5. Run everything with Docker Compose

To run PostgreSQL, the API, and the built frontend together:

```powershell
docker compose up --build
```

Then open http://localhost:3000. In this setup nginx serves the frontend and proxies `/api/` to the `api` container, so no `VITE_API_URL` is needed.

Stop the stack:

```powershell
docker compose down
```

Stop and delete the PostgreSQL data volume:

```powershell
docker compose down -v
```

## Database migrations

Run migrations from `backend`:

```powershell
uv run flask --app app db upgrade             # apply all pending migrations
uv run flask --app app db migrate -m "message" # create a migration after model changes
uv run flask --app app db downgrade -1        # revert the most recent migration
uv run flask --app app db current             # show the current revision
uv run flask --app app db history             # show migration history
```

The API container also runs `flask --app app db upgrade` on startup through `backend/entrypoint.sh`.

## Troubleshooting

**`Missing required environment variables: GOOGLE_CLIENT_ID, JWT_SECRET`**

The environment is missing required values. The backend reads existing process variables first, then `backend/.env`, then root `.env`. Check the intended local configuration without printing its contents or committing secrets.

**`connection refused` or `password authentication failed` when starting the backend**

PostgreSQL is not running or `DATABASE_URL` does not match the credentials in `POSTGRES_USER`, `POSTGRES_PASSWORD`, and `POSTGRES_DB`. Start it with `docker compose up -d db`, or clear `DATABASE_URL` to use the SQLite development database.

**Sign-in fails or the session does not stick**

- `FRONTEND_ORIGIN` must match the browser URL exactly, including the port.
- `VITE_GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_ID` must be the same client ID.
- Add `http://localhost:5173` and `http://localhost:3000` to the authorized JavaScript origins for your OAuth client in Google Cloud Console.
- Keep `COOKIE_SECURE=false` for local HTTP development.
- Open the frontend through http://localhost:5173 rather than `127.0.0.1` so the origin and cookies stay consistent.

**Frontend requests return 404 or fail with a network error**

Confirm the backend is running on port 5000 and that you did not set `VITE_API_URL`. The Vite proxy only forwards `/api` when the frontend runs with `npm run dev`.

**Port already in use**

Stop the process using port 5000, 5173, or 5432, or start the backend on another port with `--port` and update the proxy in `frontend/vite.config.ts`.

**Database schema is out of date**

Run `uv run flask --app app db upgrade` from `backend`. The backend does not create tables at startup.
