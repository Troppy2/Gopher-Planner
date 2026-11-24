# Roadmap and issue reconciliation

Reviewed against the working tree and the repository's GitHub issues on **2026-11-23**. All 15 issues returned by the issue listing were open at review time. Their original descriptions and unchecked boxes do not reliably represent current implementation.

This document distinguishes implemented foundations, partial work, and proposals. It does not close issues, assign owners, promise delivery dates, or replace issue discussion. Status here describes the working tree, which may include changes not yet released.

## Foundations already present

| Tracking issue | Evidence in the current code | Remaining distinction |
| --- | --- | --- |
| [#4: frontend/backend integration](https://github.com/Troppy2/Gopher-Planner/issues/4) | Screens call the real API through `frontend/src/api/endpoints.ts`. | Some option lists still use bundled values. External professor/grade integrations are not implemented. |
| [#7: backend expansion](https://github.com/Troppy2/Gopher-Planner/issues/7) | Models, Alembic revisions, parser/OCR, summary, coursework, and plan services/endpoints exist. | Operational hardening and broader data integrations remain separate work. |
| [#9: majors/programs](https://github.com/Troppy2/Gopher-Planner/issues/9) | Versioned JSON requirements and `GET /programs` supply the major list. | This uses files rather than the issue's proposed programs table. Profile major strings are not fully restricted to that list, and non-CS programs remain unverified. |
| [#10: full catalog](https://github.com/Troppy2/Gopher-Planner/issues/10) | Full dated exports and a repeatable importer populate SQLAlchemy `catalog_*` tables. Runtime no longer reads `courses.db`. | Scheduled refresh, richer offering semantics, and reliable exact-term availability are not complete. The old SQLite-swap proposal does not describe the current runtime. |
| [#12: backend structure/correctness](https://github.com/Troppy2/Gopher-Planner/issues/12) | Services, repositories, schemas, session helpers, JSON error handlers, tests, and P0 API flows exist. | The issue bundles many independent items. Unused required `JWT_SECRET`, production serving, auth hardening, and choosing an API host remain unresolved. CI/CD workflows exist; see the README. |

Implementation references: [API routes](../backend/app/api/v1/), [services](../backend/app/services/), [models](../backend/app/models/), [catalog importer](../backend/scripts/import_catalog.py), [frontend endpoints](../frontend/src/api/endpoints.ts), and [data guide](../backend/data/README.md).

## Proposed product and data work

### Multiple majors and premajors

[#21](https://github.com/Troppy2/Gopher-Planner/issues/21) tracks support for representing more than one major or premajor at the same time. This is proposed, not currently implemented.

**Current code boundary:** the profile currently stores one `major` string on `User`, exposes it as one `major` field in the profile API and frontend types, and uses that value as the catalog-year/program key in plan generation and summary calculation. The settings and onboarding screens also present one major combobox, and changing that value clears the saved catalog-term confirmation.

**Still needed:** define separate data and UX for majors versus premajors, decide the maximum or whether limits are unbounded, represent primary/secondary or declared/admitted status, support catalog years and requirement sets per program, merge or surface overlapping requirements, and preserve ownership and migration behavior for existing users. The implementation will need storage, migrations, profile/API wire types, onboarding/settings controls, plan/context resolution, summary and requirement progress updates, and synthetic tests.

**Out of scope for the first slice:** automatic admission-status changes, dual-degree residency/graduation-rule enforcement, cross-program course arbitration, and external university approval data. Official UMN academic rules and degree combinations must remain source-backed and advisor-verifiable.

Acceptance criteria and follow-up implementation work should remain in the new tracking issue rather than being implied as complete here.

### Liberal education, themes, writing, and double dippers

[#14](https://github.com/Troppy2/Gopher-Planner/issues/14) proposes typed designations, sourced versioned rules, a fuller per-category tracker, broader audit parsing, personalized double-dipper discovery, and dashboard changes.

**Already present:** catalog LE attributes, recognized APAS required/covered categories, labeled sample-plan slots, coverage-aware suggestions, and category-based swaps/filtering.

**Still needed:** the complete rule model and tracker described in the issue, including writing policies, source-disagreement behavior, user reassignment where appropriate, and the proposed dashboard replacement. Existing suggestion coverage is not proof that the full issue is implemented. Academic rule counts and sharing policies need official source evidence before implementation.

### Student verification of prerequisites and requirements

[#13](https://github.com/Troppy2/Gopher-Planner/issues/13) proposes course/program feedback, version-specific responses, agreement thresholds, maintainer review, and a disputed-record dashboard.

**Already present:** explicit source/review states and a program-reference validation script.

**Still needed:** feedback persistence, reporting UI, review tooling, and a policy for promoting verified records. Student votes alone must not silently turn uncertain prerequisites into enforced facts.

### Sections and instructor data

[#11](https://github.com/Troppy2/Gopher-Planner/issues/11) tracks the external-data pipeline; [#15](https://github.com/Troppy2/Gopher-Planner/issues/15) proposes recurring change detection.

The intended direction is a permitted-source adapter, normalization, snapshots/diffs, explicit provenance, and scheduled refresh. The runtime currently has no section/meeting/professor history model or weekly update job. Source permissions, endpoint behavior, term scope, rate limits, storage, and scheduling infrastructure need agreement first.

A refresh should not wipe valid data merely because a source returns an empty or unexpectedly small result. User plan changes must remain separate from public catalog updates.

### Professor ratings

[#16](https://github.com/Troppy2/Gopher-Planner/issues/16) proposes confirmed professor matching and Rate My Professors summaries or link-only behavior.

Choose and document an allowed access strategy before implementing fetching. Matching must account for ambiguity, and absent data must degrade cleanly. Current links are not a rating import, identity-match pipeline, or cached rating service.

### Historical grades

[#17](https://github.com/Troppy2/Gopher-Planner/issues/17) proposes a source-reviewed grade import, per-course/instructor distributions, provenance, and a course-drawer visualization.

There is no grade-distribution importer/model in the current backend. Confirm the dataset, terms, attribution, and course-link format before adding it. The student's own GPA summary is a different feature from historical course grade distributions.

### Optional lighter-workload suggestions

[#19](https://github.com/Troppy2/Gopher-Planner/issues/19) depends on reliable grade and professor data. It proposes an opt-in preference that ranks interchangeable valid choices and explains the ranking.

This is not implemented. The existing credit-load preference is a scheduling cap, not an ease score. Any future ranking should preserve requirements, prerequisite order, offerings, and explicit missing-data behavior; weights and minimum sample sizes remain design decisions.

### Schedule Builder and shopping-cart handoff

[#18](https://github.com/Troppy2/Gopher-Planner/issues/18) proposes a copyable course list first, then supported deep links/import/API integration if permitted.

No registration handoff is implemented. Establish what the university supports before building an authenticated integration. Gopher Planner must not collect university passwords or Duo codes. This roadmap documents the proposal; it does not begin scraping or account automation.

## Reliability and infrastructure

[#12](https://github.com/Troppy2/Gopher-Planner/issues/12) remains a broad hardening tracker. Current gaps include:

- Replacing Flask's development server in the container with a production serving strategy.
- Hosting the API: CD publishes the image and runs migrations, but deploys it only once a host's deploy hook is configured.
- API readiness checks, operational monitoring, backup/restore and retention procedures.
- Authentication rate limiting, expired-session cleanup, and account/session management.
- Finishing input-option validation and resolving remaining configuration/dependency cleanup.

These are gaps, not claims of production safeguards already being provided.

## Device and sign-in tracking

[#5](https://github.com/Troppy2/Gopher-Planner/issues/5) concerns layout shifts/device behavior; [#6](https://github.com/Troppy2/Gopher-Planner/issues/6) concerns Google client setup across devices.

The UI now has responsive layouts, shared Radix controls, a non-modal course drawer, scroll handling, and loading skeletons. Those changes do not establish that every browser/device issue in #5 is resolved. Likewise, valid server-side sign-in code does not prove the deployed OAuth client is configured for every intended origin. Closure needs a concrete device/origin verification matrix.

## Keeping this roadmap current

For each PR, state which acceptance criteria were implemented and how they were checked. Keep an issue open when meaningful parts remain, or split the remaining work with maintainer agreement. Update this document when source-backed behavior changes. Do not infer status from a checkbox alone.
