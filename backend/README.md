# Backend

Flask REST API for Gopher Planner. Uses SQLAlchemy, Alembic, PostgreSQL (user data), SQLite (course catalog seed data), and `pdfplumber` for transcript parsing.

Layering: `api` (HTTP) -> `services` (business logic) -> `repositories` (DB access) -> `models`.
Rules: verify ownership at route and service boundaries, never log transcript contents, never hold DB sessions across slow external calls, never change schema at startup (use Alembic).
