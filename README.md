# Gopher Planner

Gopher Planner is a personalized four-year college course planning tool for University of Minnesota students and academic advisors. Instead of planning one semester at a time, it uses a student's transcript, major, career goals, prerequisites, desired course load, and graduation target to build a complete degree plan.

## About the Project

### Problem

The current Gopher schedule builder is limited to one semester and offers little personalization. It is difficult for students to predict which professors may teach a course, evaluate those professors, or understand how individual courses fit into a longer-term degree plan. As a result, students may take unnecessary classes, spend additional money, or delay graduation.

### Solution

Gopher Planner acts as a centralized planning hub. A student uploads their transcript, and the application parses completed and current coursework before generating a customized four-year plan. The plan accounts for degree requirements, prerequisites, concurrent enrollment requirements, preferred credit load, desired graduation date, major, and career goals.

### Intended Users

- University students
- Academic advisors

### Goals

- Make it easier to create a complete college course plan.
- Account for courses a student has already taken or is currently taking.
- Identify prerequisites, concurrent enrollment requirements, and other degree conditions.
- Support different credit loads, graduation dates, majors, and career goals.
- Help students anticipate possible professors and review course and professor information.
- Reduce unnecessary courses, cost, and time to graduation.

### What Makes It Different

Existing schedule-building tools are primarily static and semester-based. Gopher Planner is designed to be personalized and long-term: it builds a four-year plan around each student's academic history and goals rather than only helping them select their next semester.

## Main Features

### Four-Year Planner

Students upload their transcript. Gopher Planner parses the transcript and stores courses that have been completed or are in progress, then uses that information to generate a four-year academic plan.

Current and future semesters are editable in the flow chart. Each class has a semester picker, each semester has catalog search, and current courses have editable credits. Moves into the current term become in-progress coursework; moves out become planned courses. Save and discard apply to the whole draft. Coursework changes refresh the dashboard, including separate completed, in-progress, and planned credit totals.

### Professor and Course Grade Information

For a planned course, users can view likely or historically associated professors and access their Rate My Professors information through an embedded frame or link. The application can also provide a link to average grade information for the course through Gopher Grades.

### Career and User Customization

The planner uses information supplied by the student, including:

- Major and degree program
- Career goals
- Desired graduation date
- Preferred credit load
- Completed and current coursework

## Architecture

### Frontend

- React with TypeScript
- CSS or Tailwind CSS

React provides better control over DOM updates and rendering when displaying large amounts of planning data than a plain HTML implementation.

### Backend

- Flask
- REST API
- SQLAlchemy for database ORM operations
- `pdfplumber` for transcript PDF parsing
- Google OAuth with server-side sessions

The Flask API uses SQLAlchemy repositories and services. Generation reads its inputs, releases its database transaction while planning, then revalidates the snapshot before saving.

### Databases and Caching

- One Supabase-hosted PostgreSQL database for user data, saved plans and the course catalog (`catalog_*` tables)
- Versioned JSON files for program requirements
- A simple in-memory Python dictionary for caching instead of Redis

A single database keeps catalog joins, foreign keys and concurrent writes under one set of transactions. The catalog tables are seed data: only the import script writes them.

### Authentication

Users will authenticate through Google OAuth. Access will be limited to University of Minnesota email addresses, including the `@umn.edu` domain.

### Hosting

- Host the frontend and backend on a virtual private server (VPS), such as OVHcloud or a similar provider.
- Use Cloudflare for the project domain, DNS, and reverse proxy to the VPS.

## Running Locally

### Prerequisites

Install the following before starting development:

- Node.js 20 or newer and npm
- Python 3.12 or newer
- PostgreSQL 15 or newer
- Git

### Frontend Installation

The frontend will use React with Vite and TypeScript. From the repository root:

```bash
cd frontend
npm install
npm run dev
```

The development server is typically available at `http://localhost:5173`.

### Backend Installation

Install [uv](https://docs.astral.sh/uv/), then run from the repository root:

```powershell
cd backend
uv sync
uv run flask --app app run --port 5000
```

Python 3.12 or newer is required. The API prefix is `/api/v1` and health is `/health`.

### Environment Variables

Keep credentials in `backend/.env`, never in source control. Required names are `GOOGLE_CLIENT_ID` and `JWT_SECRET`. Set `DATABASE_URL` to the intended PostgreSQL database, `FRONTEND_ORIGIN` to the frontend origin, and `COOKIE_SECURE=true` for HTTPS production hosting. The backend loads `backend/.env`, then root `.env`; existing environment variables take precedence.

The frontend uses `VITE_GOOGLE_CLIENT_ID`. Leave `VITE_API_URL` unset for Vite's local `/api` proxy, or set it to an API base ending in `/api/v1`.

### Tests

```powershell
cd backend
uv run pytest -q
cd ../frontend
npx.cmd vitest run
npx.cmd tsc -b --noEmit
```

Backend tests default to disposable migrated SQLite databases. PostgreSQL tests require a disposable local database via `TEST_DATABASE_URL`; never use Supabase or a shared database for tests. Use synthetic coursework and PDFs only.

### Docker Compose
Build image:
docker compose build

Start:
docker compose up

Stop:
docker compose up

### Database Migrations

The repository already contains Alembic migrations. After setting `DATABASE_URL` to the intended database:

```powershell
cd backend
uv run flask db upgrade
uv run flask db current
```

Create schema changes with `uv run flask db migrate -m "describe schema change"`, review the revision, and apply it with `uv run flask db upgrade`. The app never changes schema at startup.

Catalog imports replace seed tables and must be run only against an explicitly authorized destination:

```powershell
uv run python scripts/import_catalog.py --csv data/catalog-exports/courses.2026-11-23.csv
```

The importer reads `backend/data/courses.db` without modifying it, merging descriptions and liberal education designations from the full course CSV. Reviewed CSCI and MATH prerequisites take precedence; other prerequisites remain text-only warnings that do not block scheduling.

## Data Requirements

The application will use seeded and collected data for:

- Course codes, names, types, and descriptions
- Historical professors for each course
- Four-year plans for majors
- Required courses and degree-completion requirements for each major
- Course prerequisites and concurrent enrollment requirements
- Non-course prerequisites, such as college or major restrictions
- Preferred credit load
- Professor ratings and course grade information where available

The core data model centers on courses and professors. The University of Minnesota course catalog provides most course and program information; professor history and related teaching data will need to be collected separately.

Generation seeds the selected program's official sample plan, mapped backward from the graduation target, then fills unmet program requirements. Completed and registered courses are excluded. Missing liberal education categories receive labeled catalog suggestions; covered categories are skipped. Free electives are reported as credits and are not placed. Only Computer Science B.S. has a hand-reviewed requirement overlay; other majors remain unverified. Text-only prerequisites warn without blocking, and concurrent requirements are not enforced.

## Data Sources

- [University of Minnesota Course Catalog](https://umtc.catalog.prod.coursedog.com/courses)
- [University of Minnesota Programs](https://umtc.catalog.prod.coursedog.com/programs)
- [University of Minnesota four-year sample plans](https://sampleplan.umn.edu/tc-sample-plans), exported to `backend/data/catalog-exports/sample-plans.2026-11-23.csv` and built into `backend/data/sample_plans/`
- Full course snapshot: `backend/data/catalog-exports/courses.2026-11-23.csv`, including liberal education designations
- Rate My Professors, for professor ratings and reviews
- Gopher Grades, for historical course grade information

## Feasibility

The feature set is intentionally focused. The primary challenge is building and maintaining a reliable course and professor data set. The course catalog contains much of the required course, prerequisite, and program information, leaving professor history and related course-performance data as the main additional data collection needs.

## Teamwork

### Team Members

Quinn, Rohan, Inah, Cody, Sylvia, Brian, Siqi, and Saroj

### Expectations

- Each member should contribute no more than 1–2 hours per week outside of the regular Social Coding project meetings.
- The team will communicate through a shared Discord server.
- Questions, updates, and project decisions should be posted in Discord so the group can reference them.
- Members should notify the team in Discord when they will be absent and communicate any work that needs to be reassigned.
- Conflicts should be discussed promptly in Discord and resolved through an agreed-upon team decision.

## Repository

[GitHub repository](https://github.com/Troppy2/Gopher-Planner)