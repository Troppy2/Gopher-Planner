# Gopher Planner Conventions

## Project

Gopher Planner is a University of Minnesota course-planning application for students and academic advisors. It uses APAS or transcript data, completed and current courses, degree requirements, prerequisites, preferred credit load, graduation goals, major, and career goals to build personalized four-year plans.

## Planned Architecture

- Frontend: React with TypeScript, Vite, and CSS or Tailwind CSS.
- Backend: Flask, REST APIs, and SQLAlchemy.
- Transcript parsing: `pdfplumber` with manual or OCR fallback for image-only PDFs.
- User data: PostgreSQL.
- Course catalog and program seed data: SQLite.
- Schema migrations: Alembic.
- Caching: simple in-memory Python caching unless a documented requirement justifies another system.
- Authentication: Google OAuth with University of Minnesota email restrictions, using the authentication implementation selected by the project.

## Product Scope

Prioritize four-year planning, transcript upload and manual course entry, prerequisites, concurrent requirements, major requirements, professor history, Rate My Professors, Gopher Grades, career goals, dashboard progress, flow-chart planning, course catalog search, and settings.

Keep catalog and program seed data separate from user plans. Verify ownership at route and service boundaries. Do not log transcript contents or other user-sensitive data. Do not hold database sessions across slow external calls, and do not change schema through application startup.

## Implementing Features

Read [the feature implementation checklist](docs/IMPLEMENTING_FEATURES.md) before starting feature work. Follow the steps for the layers you change, from storage and services through the API and frontend. A standalone spec is optional. Use the guide's local migration and verification steps when they apply.

## Frontend Reference

Read `docs/design-rules.md` before frontend work. It is the source of truth for the maroon `#7A0019`, gold `#FFCC33`, and ivory `#E6E0D2` visual system, desktop and mobile layouts, navigation, screen requirements, accessibility, states, and Figma deliverables.

## Documentation Reference

Read `README.md` for project overview, local setup, environment variables, database migrations, data sources, hosting, and teamwork expectations. Update it when those decisions change.
