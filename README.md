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

- React with TypeScript or JavaScript
- CSS or Tailwind CSS

React provides better control over DOM updates and rendering when displaying large amounts of planning data than a plain HTML implementation.

### Backend

- FastAPI or Node.js
- REST API
- SQLAlchemy for database ORM operations
- `pdfplumber` for transcript PDF parsing
- Better Auth for authentication and Google OAuth

The backend will use a simple relational REST API. FastAPI is the preferred option because asynchronous request handling can improve responsiveness when fetching and processing data.

### Databases and Caching

- SQLite for course catalog and program information
- PostgreSQL for user data, saved plans, and other application data
- A simple in-memory Python dictionary for caching instead of Redis

SQLite is appropriate for relatively stable catalog and program data, while PostgreSQL will store user-specific and relational application data.

### Authentication

Users will authenticate through Google OAuth. Access will be limited to University of Minnesota email addresses, including the `@umn.edu` domain.

### Hosting

- Host the frontend and backend on a virtual private server (VPS), such as OVHcloud or a similar provider.
- Use Cloudflare for the project domain, DNS, and reverse proxy to the VPS.

## Running Locally

### Prerequisites

Install the following before starting development:

- Node.js 20 or newer and npm
- Python 3.11 or newer
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

If the frontend has not been scaffolded yet, create it with:

```bash
npm create vite@latest frontend -- --template react-ts
cd frontend
npm install
```

Tailwind CSS can be added later if the project chooses it for styling:

```bash
npm install tailwindcss @tailwindcss/vite
```

### Backend Installation

The backend will use FastAPI, Uvicorn, SQLAlchemy, PostgreSQL's Python driver, Alembic, and `pdfplumber`:

```bash
cd backend
python -m venv .venv
```

Activate the virtual environment:

```powershell
# Windows PowerShell
.\.venv\Scripts\Activate.ps1
```

```bash
# macOS or Linux
source .venv/bin/activate
```

Install the backend packages:

```bash
python -m pip install --upgrade pip
pip install fastapi "uvicorn[standard]" sqlalchemy "psycopg[binary]" alembic pdfplumber python-dotenv
```

Run the API from the `backend` directory with:

```bash
uvicorn app.main:app --reload
```

The API is typically available at `http://localhost:8000`, with interactive documentation at `http://localhost:8000/docs`.

### Environment Variables

Create a `backend/.env` file for local settings. Do not commit credentials or production secrets.

```env
DATABASE_URL=postgresql+psycopg://gopher:gopher@localhost:5432/gopher_planner
CATALOG_DATABASE_URL=sqlite:///./catalog.db
```

### Database Migrations

Alembic manages schema changes for the PostgreSQL database that stores user accounts, saved plans, preferences, and other user-specific data. After installing the backend dependencies and configuring `DATABASE_URL`:

```bash
cd backend
alembic init alembic
```

Configure `alembic.ini` and `alembic/env.py` to use the SQLAlchemy models and `DATABASE_URL`, then create and apply migrations:

```bash
alembic revision --autogenerate -m "create initial tables"
alembic upgrade head
```

When models change, generate a new migration and apply it:

```bash
alembic revision --autogenerate -m "describe schema change"
alembic upgrade head
```

Useful migration commands:

```bash
alembic current       # Show the current database revision
alembic history       # Show migration history
alembic downgrade -1  # Revert the most recent migration
```

The SQLite course catalog and program data should be loaded through a seed/import script rather than treated as user-data migrations. PostgreSQL must be running locally before applying PostgreSQL migrations.

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

For freshmen without transfer or completed credits, the planner will begin with a standard four-year plan and customize it using the student's major and career goals.

## Data Sources

- [University of Minnesota Course Catalog](https://umtc.catalog.prod.coursedog.com/courses)
- [University of Minnesota Programs](https://umtc.catalog.prod.coursedog.com/programs)
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