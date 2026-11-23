# Security and privacy

Gopher Planner handles academic coursework and account information. Do not publish real student records, credentials, session cookies, or transcript text in issues, pull requests, screenshots, or fixtures.

## Reporting vulnerabilities

If the repository's **Security** tab offers **Report a vulnerability**, use that private flow. Otherwise, contact a maintainer through an existing private project channel. The [repository owner](https://github.com/Troppy2) can help establish a reporting route.

If no private route is available, request one publicly without exploit steps, affected records, or credentials. Do not open a public issue containing the vulnerability itself.

Include the affected component, reproduction steps with synthetic data, expected and observed authorization behavior, relevant versions, and a suggested fix if available. Do not access another person's records or test against a shared deployment without authorization.

There is no published supported-release matrix, bug bounty, response-time commitment, or formal disclosure timeline. Coordinate disclosure with maintainers.

## Development safeguards

- Use generated PDFs and synthetic identities/coursework in tests.
- Keep `.env` files and local databases out of source control.
- Never log transcript contents, grades, tokens, or sensitive request bodies.
- Use `TEST_DATABASE_URL` only for a disposable local database. Tests drop and recreate its public schema.
- Run migrations/imports only against intended, authorized destinations.
- Do not collect University passwords, Duo codes, or registration credentials.

## Design and limits

Google credentials are verified server-side. Eligible users receive an opaque session cookie; session tokens are hashed in the database. Ownership checks belong in backend routes and persistence, independently of frontend guards.

PDF parsing and OCR run locally in the API process. The pipeline does not persist the original PDF or extracted text. It stores normalized coursework and transcript/audit metadata. Those records remain sensitive, and this behavior does not guarantee the retention settings of a deployment's infrastructure logs or backups.

The development container runs Flask's development server and applies migrations in its entrypoint. Authentication rate limiting, session cleanup, production serving, monitoring, backup/retention procedures, and other operational safeguards remain work before treating a deployment as production-ready. See [architecture limits](docs/ARCHITECTURE.md#operational-limits) and the [roadmap](docs/ROADMAP.md).
