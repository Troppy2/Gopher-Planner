# Report a problem (issue #13, first slice)

Status: approved for implementation. Base branch: `feature/requirements-modal` once it merges, otherwise `docs/codex-specs`. Work branch: `feature/report-a-problem`.

## Problem and user outcome

Only Computer Science B.S. is hand-reviewed. The other 154 majors are machine-mapped, and most course prerequisites outside CSCI and MATH are unverified catalog text. Students are the people most likely to notice a wrong rule or prerequisite, and today they have no way to tell us.

When this is done:

- A signed-in student can flag a course or a requirement group as wrong, pick a reason, and optionally add a short note, in under 15 seconds.
- They see that their report was received, and that it stays recorded if they come back.
- A maintainer can run one script that ranks the most-reported courses and requirements, with reasons and notes, and mark reports resolved or dismissed.

This slice collects and reviews reports. It does **not** change any academic data automatically.

## Read first

- `AGENTS.md`, `.claude/CLAUDE.md`, `README.md`, `SECURITY.md`.
- `docs/design-rules.md` before UI work.
- `docs/IMPLEMENTING_FEATURES.md`. This feature changes the schema, so follow its migration steps exactly.
- `docs/specs/requirements-modal.md`. It defines `ui/Modal.tsx` and the group-header slot this feature uses.

## Scope

In scope:

- A `data_reports` table, a migration, a service, and two endpoints.
- A Report button on the course drawer and on each requirement group header in the requirements modal.
- A maintainer CLI script.
- Privacy page and docs updates.

Out of scope (a later slice of #13):

- Agreement thresholds and automatic promotion of prerequisites or majors to "reviewed".
- A web dashboard for maintainers, and any admin role or admin auth.
- "Is this correct? Yes" confirmations. This slice only reports problems.
- Emailing or notifying anyone.

## Data model

New model `DataReport` in `backend/app/models/report.py`, imported in `backend/app/models/__init__.py`. Table name: `data_reports`.

| Column | Type | Notes |
| --- | --- | --- |
| `id` | int PK | |
| `user_id` | FK `users.id`, `ON DELETE CASCADE`, indexed, not null | Account deletion removes the user's reports. |
| `target_type` | String(20), not null | `course` or `requirement`. |
| `course_code` | String(12), nullable | Required for `course`. Validated with `CODE_PATTERN` from `app/schemas/coursework.py`. |
| `program_id` | String(120), nullable | Required for `requirement`. The program file `id`, resolved on the server. |
| `catalog_term` | String(20), nullable | Required for `requirement`: the program version the student saw. |
| `requirement_id` | String(64), nullable | Required for `requirement`: the top-level group id. |
| `reason` | String(40), not null | One of the reason codes below. |
| `note` | Text, nullable | Trimmed. Empty becomes null. At most 500 characters. |
| `status` | String(20), not null, server default `open` | `open`, `resolved`, or `dismissed`. |
| `created_at`, `updated_at` | DateTime(timezone=True) | Same `utc_now` pattern as the other models. |

- Add an index on `(target_type, course_code)` and one on `(target_type, program_id, requirement_id)` for the summary script.
- Store nothing else. No transcript data, no coursework, no plan, no IP address, no user agent.

**Reason codes**

| Target | Code | Label shown to the student |
| --- | --- | --- |
| course | `prerequisites_wrong` | The prerequisites are wrong |
| course | `offered_terms_wrong` | It's offered in different terms |
| course | `details_wrong` | The title, credits, or description is wrong |
| course | `other` | Something else |
| requirement | `missing_course` | A course that counts is missing |
| requirement | `course_should_not_count` | A course listed here doesn't count |
| requirement | `rule_wrong` | The number of courses or credits is wrong |
| requirement | `other` | Something else |

Keep the codes in one backend constant and mirror the labels in one frontend constant.

**Migration**

Generate a reviewed Alembic revision with `down_revision` equal to the current head. Check it with `uv run flask --app app db heads` before generating. The revision must have a real `downgrade()`. Verify:

- upgrade from the previous head with synthetic rows present,
- a clean install,
- downgrade and upgrade again,
- `uv run flask --app app db check` reports no drift.

CI runs these on PostgreSQL, so make sure they pass there too.

## API

Both routes live in a new blueprint `backend/app/api/v1/reports.py`, registered in `app/__init__.py`. Both require a session (401 otherwise). `POST` runs `check_request_origin()` first, like the other write routes. Business rules go in `backend/app/services/reports.py`.

**`POST /api/v1/reports`**

Body, one of:

```json
{ "targetType": "course", "courseCode": "CSCI 2041", "reason": "prerequisites_wrong", "note": "optional" }
{ "targetType": "requirement", "requirementId": "g-NmjYQCLR", "reason": "missing_course", "note": "optional" }
```

- Reject unknown fields, wrong types, unknown reason codes, and reason codes that don't match `targetType`. Return 400 with `{error, code: "invalid_report"}`.
- **Course:** the code must exist in the catalog or in the student's program metadata. Unknown code is 400.
- **Requirement:** the client never sends a program id. Resolve the student's program and confirmed catalog term on the server with `resolve_context(user)` from `app/services/plan.py`, then check that `requirementId` is a top-level group id in that program.
  - No program or no confirmed catalog term: 400 with `code: "program_version_unconfirmed"`.
  - Unknown group id: 400 with `code: "invalid_report"`.
- **One open report per student per target.** If the student already has an `open` report for the same target, update its reason, note, and `updated_at`, and return 200. Otherwise insert and return 201. The target is (`course_code`) for courses, or (`program_id`, `catalog_term`, `requirement_id`) for requirements. Take `lock_user(user.id)` before the read so a double click can't create two rows.
- **Rate limit:** at most 20 new reports per student per rolling 24 hours, counted from `created_at`. Updates of an existing open report don't count. Over the limit: 429 with `{error, code: "report_limit"}`.
- Response: `{ id, targetType, courseCode, requirementId, reason, note, status, createdAt, updatedAt }`.

**`GET /api/v1/reports`**

- Returns the signed-in student's own reports with status `open`, newest first, in the same shape: `{ reports: [...] }`.
- Filter by `user_id` from the session only. A student never sees anyone else's reports.

**Logging and privacy**

- Never log notes or request bodies. Log only an exception message and the report id when a write fails.
- Use `SQLAlchemyError` handling and a 503 like `profile.py`.

## Maintainer script

`backend/scripts/report_summary.py`, run from `backend` with `uv run python scripts/report_summary.py`. It reads `DATABASE_URL` like the app does.

- **Default:** a table of open reports grouped by target, sorted by distinct reporting students (descending), then the newest report. For requirements, also show the program and catalog term. Columns: target, students, reason counts, newest report date.
- `--notes`: also print each note (trimmed to 200 characters) under its target. Maintainers see notes only through this flag. Notes are student-written text, so never print user ids or emails.
- `--json PATH`: write the same data as JSON.
- `--set-status ID {open,resolved,dismissed}`: change one report's status and print the result.

The script reads and writes report rows only. It never edits program files or catalog tables. Fixing data stays a manual, reviewed change.

## Frontend

**API binding**

- In `api/types.ts`: `ReportTargetType`, `ReportReason`, `DataReport`, `NewReport`.
- In `api/endpoints.ts`: `createReport(body)` and `getMyReports()`, using `apiRequest`.
- Query key `queryKeys.reports`. Invalidate it after a successful create.

**`ReportProblemButton`** (`features/reports/ReportProblemButton.tsx`)

- Props: `target`, either `{ type: "course", courseCode }` or `{ type: "requirement", requirementId, label }`.
- It renders a quiet small button with a flag icon: "Report a problem".
- If `getMyReports()` already has an open report for the target, the button reads "Reported" with a check icon. It stays clickable, so the student can edit their reason or note; the form opens pre-filled.
- Clicking opens `ReportProblemDialog`, using `ui/Modal` (`size="md"`). If the requirements modal hasn't merged yet, create `ui/Modal.tsx` exactly as described in that spec.

**`ReportProblemDialog`**

- Title: "Report a problem". Subtitle: the course code and title, or the requirement group label.
- A radio group of the reason labels for this target type. Use native radio inputs styled to the design rules, inside a `fieldset` with a `legend`. Nothing is selected by default.
- An optional `TextArea` labeled "What's wrong? (optional)", with a live 500-character count. Hint: "Don't include personal details like your student ID or grades."
- Buttons: Cancel and Send report. Send stays disabled until a reason is chosen. Show a spinner while sending.
- Success: close the dialog and announce "Thanks. We'll review your report." in the app's live region. The button switches to "Reported".
- 429: inline Callout, "You've sent a lot of reports today. Try again tomorrow." Keep the input.
- Any other error: inline Callout, "Couldn't send your report. Check your connection and try again." Keep the input.
- Opening from inside the requirements modal: the dialog stacks on top of it. Radix supports nested dialogs; check that focus returns to the button on close and that Esc closes only the top dialog.

**Placement**

- **Course drawer** ([CourseDrawer.tsx](../../frontend/src/features/course-detail/CourseDrawer.tsx)): under the prerequisites section, a muted line "Something wrong with this course?" followed by the button with `{ type: "course" }`. Show it only when signed in.
- **Requirements modal:** in the reserved slot of each group header, the button with `{ type: "requirement", requirementId: group.id, label: group.label }`. Clicking it must not toggle the group's expansion.

**Privacy page**

In [PrivacyScreen.tsx](../../frontend/src/screens/legal/PrivacyScreen.tsx):

- Add to "What we collect": "**Problem reports:** what you reported, the reason, and your optional note."
- Say reports are deleted with your account.
- Bump `LEGAL_UPDATED`.

## Tests

Use only synthetic users, programs, and courses.

**Backend** (`backend/tests/test_reports_api.py`, using `make_user`, `login_as`, `post_headers`, `catalog`, `program_files`):

- A course report creates 201, and the same target again updates and returns 200 with one row.
- A requirement report stores the server-resolved `program_id` and `catalog_term`, and rejects client-supplied program fields as unknown.
- Validation: unknown reason, reason not matching the target type, unknown course, unknown group id, unconfirmed catalog term, note over 500 characters, a non-string note, and unknown fields.
- 401 without a session; 403 with a wrong origin.
- The rate limit allows the 20th new report and returns 429 on the 21st. Updates don't count.
- `GET` returns only the caller's open reports. A second user's reports never appear.
- Deleting a user cascades to their reports (insert directly and delete the user row).
- The summary script runs on synthetic rows: grouping and sorting are correct, `--set-status` works, and the output contains no emails.
- Migration upgrade and downgrade, if `tests/test_migrations.py` covers revisions individually.

**Frontend:**

- The button shows "Report a problem", or "Reported" when `GET /reports` has a match.
- Send is disabled until a reason is chosen. The body sent matches the contract. Success closes the dialog, announces, and switches the button.
- 429 and network errors keep the input and show the right message.
- The requirement variant inside a group header doesn't toggle the group.

Mutation-check the duplicate-target logic and the rate-limit boundary.

## Verification

From `backend`: `uv run pytest -q`, plus the migration steps in `docs/IMPLEMENTING_FEATURES.md`.

From `frontend`, in PowerShell:

- `npx.cmd vitest run --maxWorkers=1`
- `npx.cmd tsc -b --noEmit`
- `npm run build`

If `frontend/.env` sets `VITE_API_URL`, unset it for test runs.

Then smoke-test against the local API with a synthetic account:

- Report a course and a requirement group.
- Reload and see "Reported".
- Run the summary script and see both reports.

## Acceptance criteria

- [ ] `data_reports` exists through a reviewed migration that upgrades, downgrades, and passes `db check` on SQLite and PostgreSQL.
- [ ] `POST` and `GET /api/v1/reports` validate as specified, enforce ownership, dedupe per target, and rate-limit.
- [ ] The Report button works on the course drawer and on requirement group headers, with success, "Reported", and error states.
- [ ] Notes and request bodies are never logged. Reports are deleted with the account. The privacy page says so.
- [ ] The summary script ranks targets and changes status without exposing emails.
- [ ] All suites, typecheck, and build pass. Tests use synthetic data only.
