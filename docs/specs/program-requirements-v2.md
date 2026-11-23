# Program requirements v2

This is the binding requirements-data and evaluation contract for Slices 4 through 9 of [core-planner-p0.md](core-planner-p0.md). It replaces the original flat `all`/`choose` groups. Approved scope: accurately represent one officially sourced Computer Science B.S. catalog version, including alternatives and missing catalog metadata. This document specifies future work; it does not claim that the loader or engine exists.

## Sources and catalog version

Verified 2026-11-07:

- [UMN program details](https://umtc.catalog.prod.coursedog.com/programs/019627107/program-details-yXWuS): the degree requires 120 credits; program credits are separately listed as 78 to 80. These are different quantities.
- [UMN program requirements](https://umtc.catalog.prod.coursedog.com/programs/019627107/requirements-5zPfg): nested alternatives, substitutions, shared elective/math credit, and subject-specific elective constraints.
- [UMN program description](https://umtc.catalog.prod.coursedog.com/programs/019627107): effective Fall 2026.

Read the actual linked requirements and course details when preparing data. Automated summaries are discovery aids, not academic authority. Do not import an inferred total, confuse alternative lists with mandatory courses, or mix integrated master's requirements into the undergraduate degree.

Each file records `schemaVersion: 2`, `id`, `name`, `officialProgramId`, `catalogTerm`, `totalCredits`, `source`, `sources`, `courseSets`, `courseMetadata`, `groups`, and `adjustments`. `source` retains a human-readable official URL and retrieval date. `sources` maps stable keys to `{url, retrieved, section}`. Every rule, adjustment, and supplemental metadata record references a source key. Local synthetic fixtures use explicitly synthetic sources.

Reject unsupported schema versions and unknown fields. Optional top-level fields are `officialName`, `sharing`, and `catalogCompatibility`; every rule accepts only its documented fields. Credit values are finite nonnegative numbers, with positive minima wherever required; count bounds are nonnegative integers. Validate retrieval dates as dates, not just matching strings.

- `name` matches the existing profile major string. An optional `officialName` preserves the catalog's full degree name.
- Store files as `<id>--<catalog-term-slug>.json`. Lookup is by major and catalog term, never by combining files from different years.
- Ship Fall 2026 only initially. An unsupported requested catalog term returns `program_version_unavailable`, not another year's requirements.
- The generation request accepts optional `catalogTerm`. Without it, reuse the saved plan's term. With neither, list supported terms with `program_version_unconfirmed` but do not apply a candidate version's requirements or persist placements. Return a successful envelope with no placements and that warning; do not mark onboarding complete yet.
- Persist the selected term on `plans.catalog_term` using a new nullable-column Alembic revision in Slice 4. Existing plans remain unconfirmed. No user-table/profile API change is required.

## Requirement expressions

Each group has a globally unique `id`, a human-readable `label`, one existing category (`Major core`, `Math and stats`, `Elective`, `Liberal ed`), a `sourceRef`, and a `rule`. Every rule also has a globally unique `id`, `type`, and `sourceRef`.

| Type | Fields | Meaning |
| --- | --- | --- |
| `course` | `code`; sourced grade policy | One qualifying course. Alternative course codes use `any`, never an invented equivalency. |
| `all` | nonempty `children`; `allowReuse` boolean | Every child must be satisfied. Course evidence cannot satisfy different siblings unless reuse is explicitly enabled and sourced. |
| `any` | nonempty `children` | One complete child branch must be satisfied. Mixing parts of different branches does not qualify. |
| `credits` | `courseSet`, positive `minCredits` | At least that many credits from the named set. Count unique qualifying course evidence once within this node. |
| `count` | `courseSet`, optional `minCourses` and `maxCourses` | A sourced minimum or maximum number of distinct courses; at least one bound is required. |
| `review` | `message` | A known requirement that cannot be verified from available data. It remains `needs_review`; it is never silently satisfied. |

`courseSets` is an object mapping set IDs to exactly `{codes: string[], sourceRef: string}`. Code lists are explicit, nonempty and deduplicated. Do not use unrestricted subject wildcards as a substitute for an official approved-course list. Sets can overlap; total degree credits still count each selected course once. A course appearing in multiple alternatives does not become mandatory multiple times.

Every top-level group has one shared allocation pool of unique course evidence. Every course contributing to any credit total or minimum inside that group belongs to this pool. A `count.maxCourses` cap checks the entire pool filtered by its `courseSet`, not a separately chosen subset for that count node. An evaluator cannot allocate zero courses to the cap node while counting capped-set courses toward a sibling credit total. Only rules in the chosen alternative branch impose constraints; unused alternatives do not add caps. An extra course can remain outside the group as a free elective, but then contributes no credit to that group's totals.

`allowReuse` controls evidence allocation, not arithmetic. For example, a sourced combined elective group can allow one course to count toward its math subrequirement, CSCI subminimum, and overall elective total. The overall total is computed from unique evidence, not the sum of child subtotals. Maximum-count checks constrain the pool without consuming evidence themselves. Reuse between top-level groups requires `sharing`, an array of exactly `{groups: string[], sourceRef: string}` declarations, each with at least two distinct valid group IDs. Default: `[]`. Sharing is not transitive: one declaration must cover all groups that jointly use the same course. The loader rejects unknown/duplicate references.

An excerpt illustrating structure only, using synthetic courses rather than UMN requirements:

```json
{
  "id": "synthetic-intro",
  "label": "Synthetic introductory sequence",
  "category": "Major core",
  "sourceRef": "synthetic",
  "rule": {
    "id": "intro-options",
    "type": "any",
    "sourceRef": "synthetic",
    "children": [
      {
        "id": "sequence-a",
        "type": "all",
        "allowReuse": false,
        "sourceRef": "synthetic",
        "children": [
          {"id": "a1", "type": "course", "code": "TEST 1001", "sourceRef": "synthetic"},
          {"id": "a2", "type": "course", "code": "TEST 1002", "sourceRef": "synthetic"}
        ]
      },
      {"id": "sequence-b", "type": "course", "code": "TEST 1003", "sourceRef": "synthetic"}
    ]
  }
}
```

Optional `gradePolicy: {minGrade, allowS, sourceRef}` can be declared on a group or rule and inherits to its children; a more specific policy overrides it. Optional `label` is also a common rule field; progress labels fall back to the course code for a leaf or enclosing group label for other rules. `minGrade` is a valid graded letter or null when the source imposes no letter threshold; `allowS` is boolean. Missing or unverified policy is a review gap, not an invented universal C- or S/N rule. Do not assume that earning university credit satisfies the major. A completed D may earn credit in the summary but fail a requirement with a C- threshold. A completed row with unknown grade is `needs_review` for a grade-constrained rule. In-progress and future placements can satisfy only the projected evaluation, conditionally on earning the required grade; they never satisfy the completed evaluation. Use explicit grade ordering, not lexical string comparison.

Repeated attempts cannot produce duplicate requirement credit. Allocate one qualifying attempt per nonrepeatable code, choosing a qualifying attempt deterministically by highest grade, then known latest term. If repeatability or an exception changes the result and has not been sourced, return `needs_review` rather than guessing. GPA repeat-policy changes are outside this revision; preserve the existing summary contract and flag any uncertainty in degree-credit interpretation separately.

## Substitutions and adjustments

An adjustment has unique `id`, `sourceRef`, nonempty `whenAnySatisfied` requirement IDs, and nonempty `effects`. Supported effects are `{targetId, reduceMinCredits}` for a `credits` node and `{targetId, satisfy: true}` for a requirement explicitly waived by the source. Effects apply only when a complete trigger branch qualifies, once per adjustment, separately for completed and projected evaluations. Do not stack the same waiver because multiple qualifying branches or repeated attempts exist.

Reference the exact qualifying substitution branch, not a broader `any` parent that could be satisfied through a route without that waiver.

- Reject missing targets, unsupported effect types, nonpositive reductions, reductions exceeding the original minimum, and direct or indirect trigger/target cycles.
- V2 rejects multiple adjustments affecting the same target. When the official rule gives the same one-time waiver for alternative substitution routes, encode one adjustment with all qualifying branch IDs in `whenAnySatisfied`. Actual stacking needs a separately sourced contract revision under section 4.3; do not invent a `stackingPolicy` field or additive behavior.
- A waived requirement reports the adjustment and its qualifying courses in its explanation. Do not rewrite stored coursework or claim the student took the substituted course.
- Advisor approval, double-major exceptions, or transfer equivalencies without evidence become `review` nodes or unavailable branches. Do not enable an exception for every student.

## Courses absent from the bundled catalog

Do not edit `backend/data/courses.db` or import the entire university catalog. Add only the official metadata needed by this program in `courseMetadata`:

```json
{
  "TEST 1001": {
    "catalogTerm": "Fall 2026",
    "title": "Synthetic course",
    "minimumCredits": 3,
    "maximumCredits": 3,
    "offered": null,
    "prerequisites": null,
    "sourceRef": "synthetic"
  }
}
```

- Supplemental records have exactly the fields in the example. Title is a nonempty string; finite credit bounds satisfy `0 <= minimumCredits <= maximumCredits`. `offered` is null or a nonempty array of distinct `Fall`, `Spring`, `Summer` values. A nonnull `prerequisites` record is exactly `{expression, sourceRef}`: `expression` uses the catalog's `course`/`all_of`/`any_of`/`condition` tree (`course_code` and `requirements` fields), or null for an explicitly verified absence of prerequisites. Thus an outer null means unknown; a sourced record with null expression means verified none. Legacy empty/`-` offering data resolves to unknown, not an invented verified schedule.
- Title and credit bounds for every referenced course must be available from the read-only catalog or sourced supplemental metadata. Missing authoritative title/credits is a data gap: stop and ask under section 4.3. Never assign fabricated credits, a zero-credit placeholder, or a guessed course title.
- Select metadata by source compatibility with the selected catalog term, not merely by the existence of a SQLite row. Supplemental metadata records include `catalogTerm`. `catalogCompatibility` is an optional array of exactly `{catalogVersion: string, catalogTerm: string, sourceRef: string}` mappings from a verified catalog release to a program term. Empty/`unknown` catalog versions are not valid mappings. A database row's actual catalog release must match a sourced mapping before taking precedence over matching supplemental facts. The bundled catalog's `unknown` version is not evidence of compatibility.
- Matching, verified supplemental metadata overrides unknown-version or mismatched legacy catalog facts for that program. If two verified compatible sources disagree, flag `catalog_metadata_conflict` and block future placement until the conflict is resolved; do not silently choose whichever source is convenient. Coursework credits still take precedence for completed/in-progress rows without overwriting the source records.
- Unknown-version legacy catalog facts can remain visible with `catalog_version_unverified`, but must not overwrite verified target-version facts or support an unqualified schedule-complete claim. Retain the existing tentative-placement behavior for available nonempty prerequisite trees, with explicit review warnings. An absent prerequisite expression remains blocked as described below.
- `offered: null` means unknown, not Fall and Spring. A known season mismatch blocks placement. An unknown season can support a tentative placement with `offered_terms_unverified`.
- `prerequisites: null` means unknown, not no prerequisites. An explicitly verified empty prerequisite expression must carry its source. Unknown prerequisite metadata blocks future placement and returns `course_metadata_unavailable`; it does not prevent recognition of qualifying completed coursework.
- Existing catalog free-text conditions and unresolved prerequisite references retain their original nonblocking behavior, but must emit `prerequisites_require_review`. They cannot support an unqualified schedule-complete claim.
- `Course` keeps numeric credits and existing categories. Add `metadataSource: "catalog" | "program"`, `metadataWarnings: string[]`, and use `block` with a plain-language `lockReason` when scheduling metadata is insufficient. The frontend must show the reason and disable Add for that course.
- `PUT /plan` accepts a course known to the catalog or the selected program metadata. A code known to neither returns 404 `unknown_course`. Missing prerequisite metadata returns 409 `plan_invalid` with violation reason `course_metadata_unavailable`, atomically.
- A verified-source conflict uses that same violation reason with detail `catalog_metadata_conflict`. A display record can remain visible with the conflict warning, but cannot contribute assumed future credits or be placed automatically until resolved.

## Progress and generation contracts

`GET /plan`, successful `PUT /plan`, and the generated `plan` include `catalogTerm`, `availableCatalogTerms`, `warnings`, and `requirementProgress`. Supported terms come from the loader; unknown programs return an empty term list, null term and empty progress. Unconfirmed or unsupported versions are explicit warnings, not silently selected rules.

Without a saved/explicitly selected version, GET returns `catalogTerm: null`, supported terms, empty requirement progress, and `program_version_unconfirmed`; do not apply a candidate year's requirements as if selected. Existing user data remains readable. Program options and progress populate after explicit selection through generate or save. An unsupported requested generation version also returns null term and empty progress. POST generation returns HTTP 200 with `status: "succeeded"`, no planned placements, and the relevant warning for either unsupported or unconfirmed versions, leaving storage unchanged. PUT returns the documented HTTP 400 for those cases. A valid explicit dry-run selection returns that selected `catalogTerm` in the draft but writes nothing; save carries it forward explicitly.

Each progress entry has string `id`/`label`, `completedStatus`, `projectedStatus` (each `satisfied`, `unsatisfied`, or `needs_review`), `completedEvidence`, `projectedEvidence`, and `details: string[]`. Each evidence object has `matchedCodes: string[]`, `missingCodes: string[]`, and `appliedAdjustments: string[]` (adjustment IDs). For `credits` nodes add numeric `requiredCredits` and `matchedCredits` inside each evidence object; for `count` nodes add numeric `matchedCourses` plus whichever of `minCourses`/`maxCourses` the rule declares. Evidence and quantities are separate for completed and projected evaluations. `missingCodes` describes the chosen incomplete branch; it must not turn every unused alternative into a mandatory missing course. Each group status propagates from its expression; unresolved review is never converted into satisfied.

For `all`, all children must be satisfied; a definite unmet child yields `unsatisfied`, otherwise unresolved children yield `needs_review`. For `any`, a fully satisfied branch is sufficient; with no satisfied branch, unresolved branches yield `needs_review`, otherwise it is `unsatisfied`. Retain all unresolved details even when another definite deficit determines the parent status. Every finite nested rule has its own progress entry so the UI can explain the selected branch and remaining alternatives.

- Completed evaluation uses qualifying `done` coursework. Projected evaluation adds `prog` and future `plan` courses with conditional grade assumptions clearly described. Planned courses earn no completed credits or GPA.
- `Summary.percentComplete` remains credit progress, not a claim that degree requirements are met. A 100% credit metric can coexist with unmet major requirements; the UI must show that distinction.
- Generation selects whole alternatives deterministically, respects shared-credit limits, applies only justified adjustments, and does not fill mutually exclusive alternatives merely to reach a credit target.
- Stop adding courses only after both the credit goal and all machine-checkable projected requirements are met, or no feasible additions remain in the plan window. Reaching 120 credits alone is insufficient. A higher-priority unfulfilled requirement takes precedence over arbitrary elective credit.
- Sourced elective selection caps apply to requirement allocation. An extra course may still be saved as a free elective; do not reject a valid partially built plan simply because its degree requirements are incomplete.
- Graduation-credit projection deduplicates course evidence independently of requirement sharing. Unknown repeatability or credit applicability produces `requirements_need_review` instead of a false completion claim.
- A generation `status: "succeeded"` means generation ran successfully. It does not certify graduation eligibility or a globally optimal schedule.
- Keep string warning codes: existing codes plus `program_version_unavailable`, `program_version_unconfirmed`, `requirements_incomplete`, `requirements_need_review`, `course_metadata_unavailable`, `offered_terms_unverified`, `prerequisites_require_review`, `catalog_version_unverified`, and `catalog_metadata_conflict`. Include warnings in persisted-plan reads and dry runs, not just the initial generation response. The UI translates them into words.
- Unknown program still returns no placements with `program_requirements_unavailable`. Unsupported requested version returns no placements with `program_version_unavailable`. An unconfirmed version writes nothing. Other warnings can accompany a useful partial plan.

No new solver dependency is authorized. Use deterministic finite-branch evaluation and scheduling with memoization where needed. Do not claim global optimality; a greedy failure must be described as an incomplete result, not proof that the student's graduation target is impossible.

## Acceptance tests to add in order

Keep section 4.2's one-behavior red/green/refactor/full-suite cycle. All logic tests use synthetic programs and small, hand-checkable course sets; no live web dependencies.

1. Loader: v2 schema, version-specific lookup, source references, categories, globally unique IDs, set references, numeric bounds, malformed trees, unknown node types, cycles, sharing declarations, and metadata coverage. Cache clearing must work by version.
2. Requirement evaluation: nested `all`/`any`, incomplete alternative pairs, credit and count limits, subject-specific subminimum plus combined total, permitted and prohibited reuse, one-time waivers, duplicate attempts, grade thresholds, unknown grades, completed versus projected status, and review propagation.
3. Metadata: compatible catalog precedence, verified target-version overrides of legacy unknown-version data, verified-source conflict blocking, supplemental-only required course, unknown offering warnings, unknown versus verified-empty prerequisites, and no fabricated title/credits. No catalog SQLite writes.
4. Summary integration: resolve the selected program version's total, retain unknown-program fallback, and keep credit progress separate from requirement completion. Existing summary tests remain intact.
5. Engine: a four-term nested synthetic program, a case that reaches the credit goal while missing a required course, deterministic alternative selection, a justified waiver, an unmet subject quota, and incomplete metadata. Include a case where trying a second complete branch succeeds after the first is infeasible.
6. API/persistence: confirmed catalog term round trip, unsupported and unconfirmed version behavior with no writes, dry-run parity, additive progress fields on GET/PUT/generate, metadata-only course add, invalid-batch atomicity, and two-user isolation. Apply and downgrade the new nullable plan-version migration on SQLite; test PostgreSQL if available.
7. Frontend: explicit catalog-term selection, completed versus projected progress, 100% credits with unmet requirements, warning translation, disabled metadata-blocked Add actions, and supplemental-only course rendering. An unconfirmed version must not complete onboarding.

The shipped real file needs a separate source-integrity check: every listed course/rule/exception has a source and catalog term; major requirements are not replaced with an easier pathway; unsupported obligations are represented as review, never omitted as if satisfied. Tests do not validate academic truth by comparing the file to itself.
