# Degree requirements modal

Status: approved for implementation. Base branch: `docs/codex-specs`. Work branch: `feature/requirements-modal`.

## Problem and user outcome

Students cannot see what they still need for their degree. The dashboard's [RequirementProgressPanel](../../frontend/src/screens/dashboard/components/RequirementProgressPanel.tsx) lists only top-level groups with one status chip each. It names missing course codes only for unsatisfied `course` rules, and it never shows the options inside "choose 2 of these 6" or "earn 9 credits from this list" rules.

When this is done, a student can open one modal from the dashboard or the flow chart and:

1. See every requirement group for their major and catalog year, and every rule inside it.
2. Read each rule in plain words: "Complete all of these", "Complete one option", "Choose 2 of these 6", "Earn 9 credits from these courses".
3. See every course that counts, marked **Done**, **In progress**, **Planned (term)**, or **Needed**.
4. Add a needed course to their plan with one click. It goes to the earliest term where it fits, exactly like the catalog's Add button.

## Read first

- `AGENTS.md`, `.claude/CLAUDE.md`, `README.md`.
- `docs/design-rules.md` before any UI work. The modal follows its colors, states, accessibility, and mobile rules.
- `docs/IMPLEMENTING_FEATURES.md` for the layer-by-layer checklist and the commands to run.
- `docs/specs/program-requirements-v2.md` for what each rule type means. Do not reinterpret academic rules.

## Scope

In scope:

- One additive backend field (`options`) on requirement progress nodes.
- A new modal, a URL parameter to open it, and entry points on the dashboard and flow chart.
- Reusing the existing plan draft, add logic, and autosave.

Out of scope:

- Liberal education categories, themes, and writing intensive tracking (issue #14). `Liberal ed` groups that already exist in program files render like any other group.
- "Report a problem" (separate spec, `docs/specs/report-a-problem.md`). Leave a clear slot for its button in each group header.
- Changing how requirements are evaluated, program JSON files, or the generator.
- Removing courses from the plan inside the modal. Students do that in the flow chart.

## How the data works today

`GET /api/v1/plan` returns `requirementProgress`: a flat list of nodes built by `evaluate_program` in [backend/app/services/requirements.py](../../backend/app/services/requirements.py). The wire type is `RequirementProgress` in [frontend/src/api/types.ts](../../frontend/src/api/types.ts).

- Rebuild the tree with `parentId`. Top-level groups have `parentId: null`. A group's single child is its `rule`. `all` and `any` nodes have children. Node order in the list is depth-first source order. Keep that order.
- `type` is one of `group`, `course`, `all`, `any`, `count`, `credits`, `review`.
- `label` is the official label when one exists. Otherwise it is the course code for `course` nodes, or the group label for everything else. Don't show a repeated group label on a child row.
- `completedStatus` uses finished coursework only. `projectedStatus` also counts in-progress and planned courses. Each is `satisfied`, `unsatisfied`, or `needs_review`.
- `completedEvidence` and `projectedEvidence` hold `matchedCodes`, `missingCodes`, `appliedAdjustments`, and for `count`/`credits` nodes `minCourses`, `maxCourses`, `matchedCourses`, `requiredCredits`, `matchedCredits`.
- `details` holds human-readable notes (grade policy failures, waivers, review messages). Show them under the node.
- `plan.courses` already contains every course the program references, including every course-set member, with title, credits, status (`done`, `prog`, `plan`, `avail`, `block`), term, and `lockReason`. Use it for titles, credits, and per-course status. Do not fetch the catalog per course.

**The gap:** `count` and `credits` nodes don't say which courses are in their course set. The modal can't list the options without that.

## Backend change

Add `options: string[]` to every `count` and `credits` progress node: the codes of that node's `courseSet`, sorted, from `program["courseSets"][rule["courseSet"]]["codes"]`. Other node types omit the field. This is the only backend change.

- Change `visit()` in `evaluate_program`. No new route, no schema migration, no change to statuses or evidence.
- Course sets can be large (one has 370 codes). Send them anyway. The plan payload already carries those courses. The modal limits what it renders at once (see UX).
- Update `RequirementProgress` in `types.ts` with `options?: string[]`.
- Tests in `backend/tests/test_requirements.py` (or the closest existing requirements test), using the synthetic program fixtures in `backend/tests/fixtures/programs`:
  - A `count` node and a `credits` node each return their full sorted set as `options`.
  - `course`, `all`, `any`, `review`, and group nodes have no `options` key.
  - Existing statuses and evidence are unchanged (existing tests keep passing).
- Mutation check: make `options` return an unsorted or partial list, confirm a test fails, restore it.

## Opening and closing

- The modal lives in `?requirements=<groupId>` on whatever screen is open, the same way the course drawer uses `?course=CODE` (see [useCourseParam.ts](../../frontend/src/features/course-detail/useCourseParam.ts)). Use `?requirements=all` to open it with no group focused. Copy that hook's push and replace behavior so Back closes the modal.
- Mount the modal once in [AppShell.tsx](../../frontend/src/app/layouts/AppShell.tsx), next to `CourseDrawer`, so every screen can open it.
- Entry points:
  - **Dashboard:** in `RequirementProgressPanel`, make each group row a button that opens the modal focused on that group. Add a "See all requirements" ghost button in the panel header.
  - **Flow chart:** add a "Requirements" button to the toolbar near Build.
- **Course details from the modal:** clicking a course code opens the course drawer. Do this in one navigation: delete `requirements` and set `course`, pushing a history entry. Back then closes the drawer and reopens the modal. Never stack the modal and the drawer, because a Radix modal makes the rest of the page inert.
- When a focused group id is unknown (stale link, major changed), open with nothing focused. Don't show an error.

## UX

Use Radix Dialog (already a dependency). Add a reusable `Modal` primitive in `frontend/src/ui/Modal.tsx` and export it from `ui/index.ts`. The report-a-problem spec reuses it. Props: `open`, `onOpenChange`, `title`, `subtitle`, `children`, `footer`, `size: "md" | "lg"`. Use `.scrim` from `styles/index.css` for the overlay.

**Layout**

- Desktop: centered, `size="lg"` up to 880px wide and 85vh tall. The header and the filter row are fixed; the body scrolls.
- Under 768px: full-screen sheet with a close button in the header. Follow the existing drawer and bottom-sheet patterns.

**Header**

- Title: "Degree requirements".
- Subtitle: the major and "Catalog year {catalogTerm}".
- Show the existing `UnverifiedMajorNote` when the major isn't hand-reviewed.
- Keep the panel's existing line: "Your advisor and APAS have the final word."

**Summary row**

- Counts of groups by chip: Met, On track, Needs review, Short. Reuse `chip()` from `RequirementProgressPanel`; move it to `frontend/src/features/requirements/status.ts` and import it in both places.
- A two-option `SegmentedControl`: **All** | **Still needed**. Still needed hides groups whose chip is Met or On track, and hides course rows that are Done, In progress, or Planned.

**Groups**

- Each group is a collapsible section. The header shows the label, the category, the status chip, and an empty slot on the right for the future Report button.
- Default expansion: the focused group if there is one. Otherwise, every group that is Short or Needs review. Everything else starts collapsed.
- Scroll the focused group into view and move focus to its header on open.

**Rules, rendered recursively from the tree**

| Node type | Heading text | Body |
| --- | --- | --- |
| `all` | "Complete all of these" | Children in order. |
| `any` | "Complete one option" | Each child is an option card titled with its label, or "Option 1", "Option 2". Mark the option the evaluator is counting (the child whose projected evidence has matches) as "Counting toward this". Don't hide other options. |
| `count` with `minCourses` | "Choose {min} of these {options.length}" | Progress text "{matchedCourses} of {min} chosen". |
| `count` with only `maxCourses` | "Up to {max} of these count" | |
| `credits` | "Earn {requiredCredits} credits from these courses" | Progress text "{matchedCredits} of {requiredCredits} credits". Format credits like the rest of the app. |
| `course` | The course row itself (below) | |
| `review` | Callout, tone warn: "Check this one with your advisor" | The node's message from `details`. |

- When `appliedAdjustments` is non-empty, show "Adjusted: " with the details text.
- A node whose own projected status is satisfied gets a small "Met" marker on its heading.
- Flatten an `all` whose only child is another `all` or `any`, so nesting doesn't pile up headings. Never flatten across types.

**Course rows**

Each row shows the code as a link that opens course details, then the title and the credits. Its status comes from the matching `plan.courses` entry:

| Plan status | Badge | Action |
| --- | --- | --- |
| `done` | Done | None. |
| `prog` | In progress | None. |
| `plan` | Planned, {term} | None. |
| `avail` | Needed | "Add to plan" quiet button. |
| `block` | Locked | "Why?" opens course details, which show `lockReason`. |
| missing from `plan.courses` | The code alone, muted | None. This shouldn't happen; don't crash. |

- A Done course that isn't in its node's `completedEvidence.matchedCodes` (it failed a grade policy) still shows Done. The node's `details` explain why it doesn't count. Don't invent new wording.
- Hide "Add to plan" on rows under any node whose projected status is already satisfied. Keep the rows visible.
- Option lists over 12 courses: show the counted and planned ones first, then the first 12 of the rest, then "Show all {n} courses". Add a text filter input when a list has more than 30 options.
- Statuses are always text plus icon, never color alone.

**Add to plan**

Reuse the catalog's logic. Do not write a new placement algorithm.

1. Find the `Course` in `usePlan().courses`.
2. Call `targetTerm(course, courses, plan, profile)` from [planRules.ts](../../frontend/src/features/plan/planRules.ts).
3. When it returns a term, call `usePlan().add(code, term)` and announce "{code} added to {term}." in the app's live region (`announce`). Do not tell the student to save: [UnsavedPlanBar](../../frontend/src/features/plan/UnsavedPlanBar.tsx) autosaves app-wide.
4. When it returns no term, open course details for that course (same navigation as clicking the code). The drawer explains the missing prerequisites.

The row flips to "Planned, {term}" right away from the draft. Requirement statuses and chips come from the server and update after the autosave refreshes the plan query. Don't recompute statuses on the client.

**States**

- Loading: a skeleton matching the group list. Reuse `ScreenSkeletons` patterns.
- Error loading the plan: an EmptyState with "Try again" that refetches.
- `catalogTerm === null` with available terms: the panel's existing message and a link to choose a catalog year in the flow chart.
- No program file for the major: "Requirement details aren't available for your major yet."
- `plan.warnings`: list them at the bottom with `translateWarning`, as the panel does.

**Accessibility**

- Radix handles the focus trap, Esc, and focus return.
- Group headers are buttons with `aria-expanded` and `aria-controls`.
- Every Add button has an accessible name that includes the code ("Add CSCI 2041 to plan").
- Check keyboard-only operation and a 375px-wide layout.

## Files

- Backend: `backend/app/services/requirements.py` and a requirements test file.
- Frontend:
  - `api/types.ts`
  - `ui/Modal.tsx`, `ui/index.ts`
  - `features/requirements/` (new): `RequirementsModal.tsx`, `RequirementNode.tsx`, `useRequirementsParam.ts`, `status.ts`, `buildTree.ts`, `requirements.css`
  - `app/layouts/AppShell.tsx`
  - `screens/dashboard/components/RequirementProgressPanel.tsx`
  - `screens/flow-chart/FlowChartScreen.tsx`
- Docs: update `docs/feature-audit.md` (Degree requirements row) and `docs/ROADMAP.md` with what shipped.

## Tests

Use only synthetic programs, plans, and courses. Follow the MSW patterns in existing tests such as `SettingsScreen.test.tsx` and `CatalogAdd.test.tsx`.

- `buildTree.ts` unit tests:
  - It rebuilds nesting from `parentId` and keeps order.
  - It ignores a child whose parent is missing.
  - It flattens only same-kind single-child wrappers.
- `RequirementsModal.test.tsx`:
  - Opening with `?requirements=<groupId>` expands that group and focuses its header. Unknown ids open with nothing focused.
  - Every node type renders its heading text and progress numbers from evidence.
  - Course rows show each status badge, driven by `plan.courses` status.
  - "Still needed" hides met groups and done, in-progress, and planned rows.
  - Add to plan on an `avail` course updates the draft to the term from `targetTerm`, announces it, and the row shows Planned.
  - Add with no eligible term opens `?course=CODE` and removes `?requirements`.
  - No Add button under a satisfied node.
  - The catalog-year-not-chosen and no-program states render.
- Dashboard: clicking a group row opens the modal on that group.
- Mutation-check the tree builder and the Still needed filter.

## Verification

From `backend`: `uv run pytest -q`.

From `frontend`, in PowerShell:

- `npx.cmd vitest run --maxWorkers=1`
- `npx.cmd tsc -b --noEmit`
- `npm run build`

If `frontend/.env` sets `VITE_API_URL`, tests call that URL instead of their mocks. Unset it for test runs.

Then smoke-test against the local API with a synthetic account and Computer Science B.S., Fall 2026:

- Open the modal from the dashboard and the flow chart.
- Add a needed course and confirm it autosaves and survives a reload.
- Check the mobile width.

## Acceptance criteria

- [ ] `count` and `credits` progress nodes include sorted `options`; nothing else in the API changed.
- [ ] The modal opens from the dashboard (per group and "See all") and the flow chart, is linkable with `?requirements=`, and closes with Esc, the close button, and Back.
- [ ] Every group and rule renders with its plain-language heading and progress, and every option course shows its status.
- [ ] Add to plan places the course in the same term the catalog would, autosaves, and the requirement chips update after the save.
- [ ] Still needed filter, large-list truncation, and all empty and error states work.
- [ ] Keyboard and 375px layouts work. Status never relies on color alone.
- [ ] Backend and frontend suites, typecheck, and build pass. Tests use synthetic data only.
