# Slice 3.5: Consolidate branch work before Slice 4

Status: branch review and implementation plan prepared on 2026-11-22. No branch code imported or executed. Implementation remains paused until the next coding session. This supplements the [P0 spec](core-planner-p0.md), including its TDD protocol and stop conditions.

Implementation update, 2026-11-22: the user resumed coding. Live `git ls-remote --heads origin` succeeded with network escalation after the sandboxed attempt could not connect. All eight advertised heads match the cached commits below. There are no changed or newly discovered remote branches to fetch. The cached data and initial-backend refs are no longer advertised remote heads; retain them only as historical already-incorporated work. No Git refs or branches were modified. The implementation and exit-gate evidence are in the [running report](../core-planner-p0-report.md).

## Evidence boundary

Reviewed local branches and cached `origin/*` refs using `git branch -a -vv`, `git log`, `git diff`, and `git show`. `git ls-remote --heads origin` failed because GitHub was unreachable. These are cached snapshots, not verified current remote heads. Before implementing this slice, repeat the read-only remote-head check. If heads changed or additional branches exist, obtain and review their contents before treating this inventory as complete. Fetching updates writes Git refs and requires authorization under section 4.3. Do not silently use stale contents.

The current branch is `full-stack-revamp` at `392422d`, with uncommitted Slices 0 through 3. Compare candidates against the working tree, not only HEAD. Preserve those changes, all tests, the user's documentation edits, and untracked agent guidance. Do not check out, merge, cherry-pick, reset, commit, create branches, or copy a whole branch over this tree.

## Branch inventory and decisions

| Cached ref and tip | Observed work | Consolidation decision |
| --- | --- | --- |
| `origin/feat/coursework-persistence` at `aa702ff` | `CourseRecord` and `TranscriptUpload`; APAS parser; coursework replacement; calculated summary; read-only plan API; parser/model/API tests; development session script. | Primary reference for useful behaviors and test scenarios. Existing Coursework/Transcript models and contracts remain canonical. Adapt only behavior demanded by a new red test. Parser integration belongs to Slice 8 after sample verification; plan presentation belongs to Slice 6. |
| `origin/backend-expansion` at `9ebaea3` | Transcript parsing/upload, persisted Summary and encoded transcript payload, profile summary fields, frontend transcript calls. | Do not port its storage, routes, profile changes, or frontend calls. It persists raw text in debug payloads, writes PDFs to disk, lacks upload Origin enforcement, and uses header-derived XOR encoding. Its frontend calls an absent Axios-style API and invokes a hook from an ordinary function. Retain only the upload/status user-story intent already covered by Slice 8/9. |
| `origin/sylvia/academic-records` at `d2cf3a5` | Separate academic profile/course/extra-credit models, strict snapshot validation, PostgreSQL tests, opt-in development API. Tip explicitly says based on old main, not for merge. | Reuse validation and database-test ideas selectively. Do not import its replacement app/auth/database bootstrap, dev identity API, separate student identity, or old migration baseline. Unmapped credit and grading-basis schema expansion are deferred pending a separate approved contract. |
| `origin/feat/static-frontend` and `origin/database-migration-deletion` at `371708e` | Older frontend lineage and agent-document removal; history includes patches similar to current UI work. | No wholesale port or deletion. Compare content before claiming a missing feature, since different commit IDs can contain equivalent work. UI changes outside P0 stay deferred. |
| Historical cached `origin/feat--init-backend,login,course-search` at `50cb4ee`; `origin/data/MATH+CSCI-courses` at `535d871` | Backend/auth/catalog and catalog data already present in current history. Neither ref is advertised by the live remote on 2026-11-22. | Already incorporated at the committed baseline; do not replay or describe as live remote branches. |
| `origin/feature` at `ecb7e41` | Older design/concept work; its tree lacks much of the current application. | Historical design reference only. Do not restore its tree. |
| `origin/main`, `origin/full-stack-revamp` at `392422d` | Current committed baseline. | No additional work to import from these cached tips. |

Local named branches point to the same reviewed tips where counterparts exist. Stash and agent checkpoint refs are not teammate branches and are outside this consolidation request.

## Compatibility findings

- Persistence branch uses `completed` / `in_progress`; our public coursework contract uses `done` / `prog`. Its GET coursework omits `skipped`. Keep our vocabulary, skip state, provenance, validation, and owner filtering.
- Its summary duplicates our existing calculations, uses different source labels, and rounds percentage differently. Keep the current single grade table, half-up rounding, null metrics, and excluded grades. No second Summary table or calculator.
- Its plan builder labels requirements by subject, flattens prerequisite edges, derives current term from coursework, and has a different default window without the specified maximum. These are not authoritative academic or scheduling semantics. Retain v2 expression trees, version selection, metadata warnings, bounded terms, and the P0 calendar rules.
- Its OCR route returns 501 without authentication or ownership checks. Future Slice 8 tests must require authentication, allowed Origin, owner lookup, and 404 for another user's resource before returning `ocr_unavailable`.
- Its transcript upload reads the session before PDF parsing and does not explicitly close the transaction before slow work. Use the spec's capture-identity, release-session, parse, then fresh atomic-write boundary.
- Its parser hardcodes APAS line shapes and transfer markers. Code and synthetic examples are not proof of the real format. Do not copy branch fixtures or student records. A real redacted sample remains a stop condition; do not infer undocumented transfer grades or misclassify requirement-option lines as completed courses.
- Its model tests suggest useful null-term duplicate and database-constraint cases. Current API validation catches duplicates, but a nullable term in a conventional UNIQUE constraint may still permit duplicate direct inserts. Verify the actual migrated database before changing it.
- Supabase PostgreSQL, Flask, SQLAlchemy, Alembic, existing Google sessions, and the read-only catalog remain the architecture. No new dependency or authentication mechanism is approved by this review.

## Ordered implementation plan

### 3.5a: Confirm scope and baseline

1. Verify branch freshness as above and update this inventory if needed. Record any unavailable source explicitly.
2. Read the complete P0 spec, v2 appendix, this plan, and current implementations before adapting code.
3. Run `uv run pytest -q` from `backend`; compare with the last recorded 104 passes. Run frontend typecheck and build to reconfirm the recorded TS7006 baseline. Separate unrelated failures.
4. Map each candidate behavior to an existing test, a missing P0 test, or a deferred non-goal. Already passing characterization tests do not justify artificial production changes.

### 3.5b: Harden existing persistence through TDD

For each behavior below, follow section 4.2 separately: one red test, targeted run confirming the intended failure, smallest implementation, refactor, full backend suite. If already green, record it as characterization and make no production change.

- Database rejects a duplicate owner/code attempt with null term, while allowing another user's identical code and distinct known-term attempts. Exercise a direct database write, not only the PUT validator.
- Preserve the API's atomic replacement, two-user isolation, server-controlled provenance, skipped state, transcript SET NULL behavior, and user cascades while making any constraint fix.
- If a constraint change is required, add a new forward Alembic revision; preserve shipped and Slice 1 revisions. Test empty and populated upgrades, downgrade, no drift, and rollback of rejected writes. Never discard existing duplicates automatically. If legacy rows prevent upgrade, stop for an explicit data-repair decision.

Do not broadly import all constraints from another model. Constraints for new credit-source fields, extra credits, grading basis, and changed numeric ranges require a separately approved data contract. Do not add them here.

### 3.5c: Carry forward future-slice reuse

| Target slice | Candidate reuse | Required tests before adaptation |
| --- | --- | --- |
| 4 | Academic snapshot's explicit catalog-version concept. | Existing v2 term-selection, version-isolation, loader, migration and summary-lookup tests remain mandatory. No parallel profile schema. |
| 5/6 | Pure term helpers, completed/current coursework projection, owner-filtered plan reads from persistence branch. | Calendar boundaries; bounded Fall/Spring window; unknown terms; real prerequisite trees; missing metadata; correct earned base credits; two-user isolation; existing saved edits retained. Test P0 behavior, not the candidate's incompatible output. |
| 8 | Pure APAS parser separation, deduplication, no-text detection, transaction-owned replacement and status counts. | Verified redacted sample first; synthetic sanitized fixtures only; requirement-option rejection; repeats by term; in-progress grade null; malformed/unsupported formats; failed upload leaves coursework unchanged; successful atomic write and provenance; filename sanitization; size/signature validation; no retained PDF/raw text; auth/Origin/404 ownership, including OCR. |
| 9 | Transcript request/status wiring intent. | Component/API tests for multipart FormData using the existing client contract, credentials, errors and fallback; no hook in endpoint helpers; loading and summary-error states. Install only the already approved frontend test stack in Slice 9. |

Candidate tests are design input, not automatically trusted regressions. Rewrite one relevant behavior at a time against our canonical contracts with synthetic data, observe its red state, then adapt only the necessary code. Record source ref, commit, path, adopted behavior and intentional differences. Do not bulk-copy test suites or weaken our assertions to match another branch.

### 3.5d: Exit gate

- Branch inventory is verified current. Unavailable access is a recorded blocker, not a passed exit criterion; do not resume Slice 4 while freshness is unverified.
- Every inspected behavior has a disposition: already covered, adopted with red/green evidence, scheduled in a named future slice, or deferred with reason.
- All existing and new backend tests pass; migration checks pass if migrations changed. Perform and restore one mutation check for an adopted behavior, then rerun the full suite.
- Frontend baseline failures remain separately recorded unless an explicitly scoped future change resolves them. No frontend feature port in 3.5.
- Update the running report with exact commands, red failures, source commits, files, review results, and remaining blockers. Do not claim branch suites or PostgreSQL checks passed without running them.
- Supabase migration execution requires an explicitly designated disposable test database. Never run teammate tests or migrations against a shared or production database. Lack of a safe PostgreSQL target leaves PostgreSQL verification pending, not implicitly green.
- Resume Slice 4 only after this gate and the user's coding pause are cleared. Slice 3.5 does not authorize code today or bypass the transcript sample/source/dependency stop conditions.
