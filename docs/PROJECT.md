# Gopher Planner project guide

Gopher Planner turns coursework and degree requirements into a multi-semester planning workspace for University of Minnesota students and academic advisors. This document explains the product. For implementation details, read [ARCHITECTURE.md](ARCHITECTURE.md); for proposed work, read [ROADMAP.md](ROADMAP.md).

## The problem

Choosing next semester's classes requires more than finding an open course. Students need to account for prior coursework, prerequisite chains, degree rules, term availability, workload, and graduation goals. A change of major or an imported audit can change that picture again.

The planner brings those inputs together, suggests a starting schedule, and makes revisions visible. It should help a student explain a plan to an advisor and understand unresolved requirements.

## Users and goals

| User | What the planner should help them do |
| --- | --- |
| A new student | Start from a published sample plan and understand the sequence of courses. |
| A student with existing credit | Import or enter coursework and avoid planning the same earned/registered course again. |
| A student changing direction | Select another major, confirm a catalog year, and review the resulting requirements. |
| A student adjusting workload | Move classes between terms, edit current credits, and see scheduling conflicts. |
| An advisor | Review completed versus projected progress and identify decisions that still need academic review. |

The current product stores career goals, but it does not implement a career-based recommendation model or an ease score. Preferred credits are scheduling inputs, not a measure of course difficulty.

## Core workflow

### 1. Sign in

Sign in with Google using a verified `@umn.edu` account. The server validates the credential and creates its own session. The browser does not decide eligibility or ownership.

### 2. Add coursework

Choose PDF upload, manual entry, or skip during onboarding. Imported and manually entered courses become normalized coursework records with a code, credits, status, term, and optional grade.

For a PDF, the server extracts text first and uses local OCR when extraction is empty or appears misread. The user can correct courses later in Settings. An unreadable document produces an explicit recovery state, not an empty success result.

Re-upload replaces imported rows while preserving manual attempts for the same course/term. Deleting coursework does not delete the major or the available program files. Uploading another report does not select a major automatically.

### 3. Choose a profile and catalog year

Select a major, standing, credit preference, graduation target, and optional career goal. Supported majors come from the program API; other option lists still contain bundled values.

Requirements are selected by major and catalog term together. The planner asks for explicit year confirmation when a supported major has no selected version. It does not combine requirements from different years or silently choose a candidate year.

Changing major clears the previous major's unsaved draft and resets catalog-year confirmation. Existing coursework and saved planned courses are retained, so the student can review and rebuild deliberately.

### 4. Build a plan

The generator starts with the selected program's published sample-plan sequence when available. It maps the sequence onto the graduation target, skips satisfied work, and fills remaining machine-checkable rules.

If the current semester has no in-progress coursework, generation includes it as a planning term. Suggested current courses remain planned until explicitly moved into enrollment. Existing current enrollment is preserved.

Generation checks structured prerequisite order, known offering seasons, and credit capacity. It may return an incomplete schedule with warnings. That result is useful evidence of unresolved work, not proof that no feasible plan exists.

Onboarding builds a persisted plan. Building from the planner creates a preview draft. The student reviews that draft and chooses **Keep this plan** or discards it.

### 5. Edit and review

The semester view shows current and future terms with course rows. The graph shows prerequisite relationships and offers an alternative view of the same plan. The catalog and course drawer support finding and inspecting additional courses.

Ordinary plan, profile, and coursework edits autosave after a pause. Generated replacement plans wait for explicit confirmation. Validation failures preserve edits and show actionable reasons. Dashboard queries refresh after relevant saves/imports so credit and requirement progress reflect saved changes.

Moving a class into the current term makes it in-progress coursework. Moving it out makes it a planned course. These changes affect both persistence and progress; they are not just a visual rearrangement.

## Screens

| Screen | Primary content | Important states |
| --- | --- | --- |
| Login | Project identity and Google sign-in. | Session check, invalid account, unavailable sign-in. |
| Onboarding | Coursework method, profile, catalog-year confirmation, generation. | Upload/parsing progress, manual correction, skip, retry. |
| Dashboard | GPA, earned credits, credit progress, current/future classes, requirements, profile details. | Layout-matched skeletons, unavailable summary, no coursework, unknown requirements. |
| My plan | Semester cards or graph, course actions, catalog year, build action. | Initial skeleton, build progress, draft confirmation, save failure, invalid move. |
| Catalog | Search, filters, result counts, paginated rows, course drawer. | Initial skeleton, background update, no matches, retry. |
| Settings | Profile/planning preferences and coursework editing/re-upload. | Field/row skeletons, autosave, failed option loading, correction and retry. |

Shared course details contain catalog metadata, prerequisite information, planning actions, and links where available. Unknown professor or grade-history data must remain unavailable rather than being presented as a populated integration.

## Progress and terminology

| Term | Meaning |
| --- | --- |
| Completed | Coursework marked done. Whether it earns credit or satisfies a particular rule depends on its grade and that rule's policy. |
| In progress | Current coursework that can count toward projected progress, but is not completed evidence. |
| Planned | A proposed course placement stored in a plan or temporary draft. |
| Available / locked | Presentation states derived from metadata and scheduling checks; not registration or seat availability. |
| Credit progress | Earned credit relative to a program total, or the application's fallback total when no program is resolved. |
| Requirement progress | Evaluation of specific rules, distinguishing completed evidence from projected completion. |
| Needs review | A condition, source disagreement, or policy the application cannot certify automatically. |
| Slot | A label describing why a suggested course was placed, such as a particular LE category. |
| Free elective credits | Remaining credits needed for the total after projected credit is considered. These are reported, not filled with arbitrary courses. |

Credit progress is not degree certification. A student can meet a total-credit target while missing a specific required course or an unresolved review condition. GPA is calculated from entered/imported graded coursework; it is not an official transcript calculation.

## Accuracy and source boundaries

Course metadata, program rules, and sample plans are distinct inputs:

- The runtime catalog is imported into `catalog_*` tables from bundled/detailed public exports.
- Program requirements are versioned JSON, with provenance and explicit review states.
- Sample plans describe a suggested sequence. They are not additional authoritative degree rules and are not catalog-version-specific.
- Parsed APAS category status, when recognized, helps determine which LE slots still need suggestions.

Only Computer Science B.S. has a rule-by-rule reviewed overlay. The other program files are machine-mapped. Structured reviewed prerequisites cover CSCI/MATH; text-only prerequisites elsewhere prompt review and do not become hard scheduling blocks.

The current sample-plan snapshot covers 161 pages, of which 155 match programs. Six unmatched pages remain documented in [the data guide](../backend/data/README.md). No degree equivalence is guessed for them.

The application does not yet provide complete versioned LE core/theme/writing rules, concurrent-enrollment enforcement, exact term sections, instructor history, seat availability, or registration-cart access. Read the [roadmap](ROADMAP.md) for the corresponding proposals and dependencies.

## Privacy and accessibility

The upload service processes PDFs locally and stores normalized rows and audit metadata, not the PDF or extracted document text. Stored records still contain academic information and require owner-filtered access.

Tests, fixtures, public reports, and screenshots must use synthetic data. Never publish real audits to explain a parser problem. See [SECURITY.md](../SECURITY.md).

The UI uses the project's maroon/gold/ivory design system, keyboard-accessible shared controls, responsive layouts, non-graph planning views, and skeletons matching the content being loaded. Loading, failure, and missing data should be understandable without interpreting color alone. The [design rules](design-rules.md) define the full UI target.

## Project documentation and maintenance

The README is the entry point for setup and contribution. This guide describes product behavior. The architecture explains technical boundaries. The roadmap reconciles current code with GitHub proposals.

Older feature audits and handoffs remain useful history, but can describe superseded implementations. Changes should update the relevant current document and identify any issue criteria that remain incomplete. An issue should not be treated as entirely complete merely because a related endpoint or UI control exists.
