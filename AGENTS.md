# Gopher Planner Agent Instructions

## Project

Gopher Planner is a University of Minnesota course-planning application for students and academic advisors. It creates personalized four-year plans from APAS/transcript data, completed and current courses, degree requirements, prerequisites, preferred credit load, graduation goals, major, and career goals.

The repository contains:

- `frontend/`: React frontend and responsive planning UI.
- `backend/`: Flask backend, SQLAlchemy data access, transcript parsing, REST endpoints, and migrations.
- `docs/design-rules.md`: frontend design source of truth for Figma and implementation.
- `README.md`: project overview, architecture, setup, and migration guidance.

## Product Scope

Prioritize work that supports:

- Four-year academic planning.
- APAS or transcript upload and parsing.
- Manual course entry when parsing is unavailable.
- Course prerequisites and concurrent requirements.
- Major and degree-program requirements.
- Professor history, Rate My Professors links, and Gopher Grades links.
- Career and user customization.
- Dashboard progress, flow-chart planning, course catalog search, and settings.

Do not import assumptions, terminology, routes, components, or architecture from unrelated projects.

## Technical Direction

- Frontend: React with TypeScript preferred, Vite, and CSS or Tailwind CSS.
- Backend: FastAPI with Uvicorn and REST APIs.
- ORM: SQLAlchemy.
- Transcript parsing: `pdfplumber`, with a clear manual or OCR fallback for image-only PDFs.
- Authentication: Better Auth or the repository's selected authentication implementation, with Google OAuth and University of Minnesota email restrictions.
- User data: PostgreSQL.
- Course catalog and program seed data: SQLite unless the implementation establishes a different documented boundary.
- Migrations: Alembic for SQLAlchemy/PostgreSQL schema changes.
- Caching: simple in-memory Python caching is acceptable for stable, low-risk data; do not add Redis without a concrete need.

When implementation details are undecided, preserve the choices documented in `README.md` and update the documentation when a decision becomes final.

## Frontend Rules

Read `docs/design-rules.md` before making frontend changes. Preserve its visual direction:

- Maroon `#7A0019`, gold `#FFCC33`, and ivory `#E6E0D2` are the primary palette.
- Use warm ivory foundations and restrained frosted/glass surfaces.
- Design desktop and mobile states together.
- Desktop uses a persistent navigation rail when space allows; mobile uses bottom navigation.
- The core destinations are Dashboard, Flow chart, Course catalog, and Settings.
- Include loading, empty, error, unavailable, completed, locked, and unsaved states.
- Keep academic progress visible and make complex prerequisite details available on demand.
- Maintain accessible contrast, keyboard focus, semantic headings, named icon buttons, 44px touch targets, reduced-motion support, and a text/list alternative for the flow chart.
- Use Lucide or an existing icon library where available instead of hand-drawn interface icons.
- Avoid decorative card nesting, oversized marketing heroes, purple-first palettes, and text-only controls where a familiar icon communicates the action.

Do not replace the established Gopher Planner visual language with generic dashboard styling.

## Backend and Data Rules

- Keep user data isolated by authenticated user and verify ownership at the route/service boundary.
- Treat transcript text, course history, career goals, and profile data as user-sensitive information.
- Do not log uploaded transcript contents, OAuth credentials, database URLs, or other secrets.
- Use structured parsing and validation for APAS, course prerequisites, degree requirements, and seeded catalog data.
- Keep course catalog/program seed data separate from user plans where the data model calls for it.
- Prefer async FastAPI patterns for I/O-bound work and avoid blocking the event loop with document parsing or long-running operations.
- Do not hold database sessions or connections open across slow external calls.
- Add Alembic migrations for PostgreSQL schema changes; do not silently modify the database schema through application startup.
- Make migrations reversible when practical and document required environment variables and migration commands.

## Working Practices

- Before starting work, read this `AGENTS.md` and inspect the relevant sections under
	`.claude/rules/`, `.claude/skills/`, `.claude/reference/`, and `.claude/session-notes/`
	when those directories or files exist. Read only material relevant to the task; treat
	historical session notes as context, not active instructions.
- Read the nearest relevant implementation, test, and documentation before editing.
- State a local hypothesis and a focused validation check before the first substantive edit.
- Make the smallest change that addresses the request. Preserve unrelated user changes.
- Do not reset, checkout, delete, or overwrite user work without explicit approval.
- Do not commit, push, merge, or create branches unless explicitly requested.
- Keep public APIs and existing data contracts stable unless the task requires a deliberate change.
- Add focused tests for behavior changes, especially transcript parsing, prerequisite logic, plan generation, ownership, and responsive UI behavior.
- Update `README.md` or the relevant document when setup, architecture, data sources, or product decisions change.

## Validation

Use the narrowest available check first, then broaden only as needed:

- Frontend: run the repository's typecheck, targeted tests, and production build when available.
- Backend: run targeted tests, syntax/import checks, and migration checks when available.
- Documentation: check Markdown structure, links, commands, and whitespace.
- For responsive UI changes, verify both a desktop viewport and a mobile viewport when a browser harness is available.
- Report pre-existing failures separately from failures introduced by the change.

## Communication

Use concise, direct updates. Explain assumptions and blockers. In the final response, summarize changed files, validation performed, and any remaining limitations. Avoid references to unrelated repositories or historical work that is not present in Gopher Planner.
