# Running Gopher Planner Locally

This guide covers running the React frontend and Flask backend on your machine.

## Ports

| Service | URL | Notes |
| --- | --- | --- |
| Frontend (development) | http://localhost:5173 | Vite dev server |
| Frontend (Docker) | http://localhost:3000 | nginx serving the production build |
| Backend API | http://localhost:5000 | Flask, health check at `/health` |
| PostgreSQL | localhost:5432 | Only needed when using PostgreSQL |

## Prerequisites

- Node.js 22 or newer and npm
- Python 3.12 or newer
- [uv](https://docs.astral.sh/uv/getting-started/installation/) for the backend
- Docker Desktop if you want to run PostgreSQL or the full stack in containers
- A Google OAuth client ID (see `VITE_GOOGLE_CLIENT_ID` below)

## 1. Environment variables

The backend and Docker Compose both read the repository root `.env` file. The backend does **not** read `backend/.env`.

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
npm run build      # typecheck and production build into dist/
npm run preview    # serve the production build on port 5173
```

Note: several screens still read from mock data in `src/api/mock/`, while the sign-in and profile calls use the real backend. The frontend README explains how to replace the mocks.

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

The root `.env` file is missing or incomplete. The backend loads it relative to the repository root, not `backend/.env`.

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
