# Onboarding UX Spec

Audit of every onboarding screen and state, 2026-11-24. 30 issues: 16 fixed on `ux/onboarding-audit` (not merged yet), 14 still open.

- **Scope:** Step 1 Coursework (upload, manual entry, skip), Step 2 Profile, Step 3 Building your plan. Every loading, empty, error, success and retry state.
- **Method:** the frontend ran locally with a mocked API so each state could be forced, at 1280 px desktop and 390 px mobile. "Before" screenshots come from `main` at `9c7d461`; "after" screenshots come from `ux/onboarding-audit`.
- **Status:** **Fixed** = changed on `ux/onboarding-audit`, checked in the browser, frontend tests (114) and production build passing. **Open** = still needs a change or a decision.
- **Rules:** [`design-rules.md`](design-rules.md#onboarding) says onboarding is skippable where data is optional, resumable, validates one step at a time, and keeps coursework when the student goes back.

Screenshots live in [`onboarding-ux/`](onboarding-ux/).

## Step 1: Coursework

| # | Issue | Expected behavior | Status |
| --- | --- | --- | --- |
| 1.1 | A Continue error stays on screen after the student fixes it. "Upload your APAS PDF, or choose another option" stays during and after a successful upload; "Add at least one course" stays after a course is added. | The error clears as soon as the student uploads a file or adds a course. | Fixed |
| 1.2 | **Data loss.** "Correct these courses" turns parsed transcript rows into manual rows and drops each course's term and grade, so saving loses grades. | Corrected rows keep their transcript term and grade. An in-progress row still takes the current term. | Fixed |
| 1.3 | **Data loss.** "Skip for now" saves an empty course list, deleting coursework already saved, with no warning. | When courses exist, the Skip panel warns "Skipping removes the N courses you already added." | Fixed |
| 1.4 | A server failure during upload is titled "Couldn't use that file", which blames the student's file. | A rejected file says "Couldn't use that file". A failed upload says "The upload didn't finish". | Fixed |
| 1.5 | After Add on a search result, the row leaves the list and keyboard focus drops to the page. | Focus returns to the search box. | Fixed |
| 1.6 | At 390 px, "Your courses" rows line up differently: short titles keep the status control inline, long titles wrap it below. | On mobile the status control and remove button always sit on their own line. | Fixed |

**1.1 Stale error after a successful upload**

| Before | After |
| --- | --- |
| ![Error still shown under a parsed upload](onboarding-ux/1-1-stale-error-before.png) | ![No error after a parsed upload](onboarding-ux/1-1-stale-error-after.png) |

**1.3 Skip with courses already added**

| Before | After |
| --- | --- |
| ![Skip panel with no warning](onboarding-ux/1-3-skip-existing-before.png) | ![Skip panel warning that 3 courses will be removed](onboarding-ux/1-3-skip-existing-after.png) |

**1.4 Server failure during upload**

| Before | After |
| --- | --- |
| ![Failed upload titled Couldn't use that file](onboarding-ux/1-4-upload-failed-before.png) | ![Failed upload titled The upload didn't finish](onboarding-ux/1-4-upload-failed-after.png) |

**1.6 Mobile course rows**

| Before | After |
| --- | --- |
| ![Rows with mixed control placement](onboarding-ux/1-6-mobile-rows-before.png) | ![Rows with controls on their own line](onboarding-ux/1-6-mobile-rows-after.png) |

## Step 2: Profile

| # | Issue | Expected behavior | Status |
| --- | --- | --- | --- |
| 2.1 | **Plan bug.** A blank graduation target is saved as "Spring 2028". A freshman starting Fall 2026 gets a plan of about three terms. | Blank is saved as blank; the planner then uses its standard 8 terms. | Fixed |
| 2.2 | The hint under the form promises "we ask you to confirm a graduation target before the plan is final". No such step exists. | Hint: "If you leave these blank, we plan 15 credits per term over a standard four years. You can change both later in Settings." | Fixed |
| 2.3 | Graduation target options are a hardcoded list, Fall 2027 to Spring 2030. | The next 12 Fall and Spring terms after today. | Fixed |
| 2.4 | Name is empty even though Google sign-in already gave it. | Name is prefilled from the signed-in account. | Fixed |
| 2.5 | A submit with errors leaves focus on the submit button. | Focus moves to the first field with an error. | Fixed |
| 2.6 | A typed major that is not in the list (for example "computer science") is accepted silently, and the plan gets no program courses. | When the field loses focus, a warning says there are no requirements for that major and asks the student to pick from the list. | Fixed |

**2.2 and 2.4 Profile defaults**

| Before | After |
| --- | --- |
| ![Empty name and the old hint](onboarding-ux/2-profile-defaults-before.png) | ![Prefilled name and the new hint](onboarding-ux/2-profile-defaults-after.png) |

**2.6 Major not in the list**

| Before | After |
| --- | --- |
| ![Free-text major with no feedback](onboarding-ux/2-6-unknown-major-before.png) | ![Warning under an unknown major](onboarding-ux/2-6-unknown-major-after.png) |

## Step 3: Building your plan

| # | Issue | Expected behavior | Status |
| --- | --- | --- | --- |
| 3.1 | The step spinner keeps spinning while the screen waits for a catalog year and after a failed build. | Nothing spins while the screen waits on the student or after a failure. | Fixed |
| 3.2 | The subtitle says "This takes a few seconds" during the failed and version-confirmation states. | Subtitle matches the state: "One choice before we finish", "Something went wrong", or "This takes a few seconds". | Fixed |
| 3.3 | No Back button, so a wrong major or graduation target cannot be fixed from this step. | Back to Profile until the plan is saved. | Fixed |
| 3.4 | The "Choose the catalog year you follow" heading sits on the panel's border line. | The heading sits inside the panel like other panel headings. | Fixed |

**3.1, 3.3 and 3.4 Catalog year choice**

| Before | After |
| --- | --- |
| ![Spinner on the catalog step, heading on the border, no Back](onboarding-ux/3-catalog-choice-before.png) | ![Paused steps, heading inside the panel, Back button](onboarding-ux/3-catalog-choice-after.png) |

**3.1 to 3.3 Failed build**

| Before | After |
| --- | --- |
| ![Spinner still running after a failure](onboarding-ux/3-build-failed-before.png) | ![Paused steps, failure subtitle, Back button](onboarding-ux/3-build-failed-after.png) |

## Open inconsistencies

These are on `ux/onboarding-audit` too. Each needs a change or a decision.

| # | Area | Issue | Proposed fix |
| --- | --- | --- | --- |
| O.1 | Buttons | Step 1 shows two maroon primary buttons at once: "Choose file" in the drop zone and "Continue". | Make "Choose file" a secondary (ghost) button; one primary per screen. |
| O.2 | Buttons | Secondary actions use three styles in one panel: ghost "Correct these courses", quiet "Upload a different file", ghost "Add". | Pick one secondary style for in-panel actions. |
| O.3 | Validation | Each step validates differently. Step 1 keeps Continue enabled and errors on click, Step 2 errors on submit, Step 3 disables "Build my plan" until a year is picked. | Use one pattern: keep primary buttons enabled and show errors on click. |
| O.4 | Loading | Step 1 Continue changes to "Saving" with no spinner. Step 2 shows a spinner next to its label. | Same spinner and label change on every primary button. |
| O.5 | Errors | In the no-text and failed-parse states, clicking Continue adds a red error repeating the warning already on screen. | Do not add the Continue error when the upload panel already explains the problem. |
| O.6 | Copy | The option card says "APAS or transcript PDF", but the drop zone and errors say "APAS PDF". | Use one term everywhere. |
| O.7 | Copy | The parsed upload status reads "Read", which is ambiguous. | "Courses found" or "Read successfully". |
| O.8 | Layout | The Skip panel wraps an info callout inside a panel, a box in a box. No other option does this. | Show the message as plain text in the panel. |
| O.9 | Layout | On the catalog year step, "Build my plan" sits inside the panel while Back sits in the action row below it. | Put both in the action row, like Steps 1 and 2. |
| O.10 | Navigation | The step header shows "1 of 3" with no step names. | Name the steps: Coursework, Profile, Plan. |
| O.11 | Navigation | The logo links to Step 1 on every step. Clicking it on Step 3 drops the student back to the start. | Link the logo to the current step, or make it plain text during onboarding. |
| O.12 | Navigation | A student who finished onboarding can open `/onboarding/*` again and rebuild their plan. | Redirect onboarded students to the dashboard. |
| O.13 | Resume | After a page reload, Step 1 resets to Upload. A saved upload or a saved skip is not restored; only manual rows are. | Restore the saved choice and show saved transcript courses. |
| O.14 | Search | A one-letter search shows nothing with no hint, and every keystroke sends a request. | Show "Type at least 2 characters" and wait about 250 ms after typing stops. |

Also open, outside onboarding: Settings still uses the hardcoded graduation target list from 2.3. PR #20 adds `GET /api/v1/options` with server-generated targets, which would replace both.

**O.5 Duplicate error on an unreadable PDF**

![Warning and a duplicate red error](onboarding-ux/open-no-text-duplicate.png)

**O.1 Two primary buttons** can be seen in the 1.4 screenshots above: "Choose file" and "Continue".

## Checklist

| # | Item | Status | Files |
| --- | --- | --- | --- |
| 1.1 | Clear stale Continue errors | Fixed | `CourseworkScreen.tsx` |
| 1.2 | Keep term and grade when correcting | Fixed | `coursework.ts`, `onboarding.store.ts`, `ApasUploader.tsx` |
| 1.3 | Warn before Skip removes courses | Fixed | `CourseworkScreen.tsx` |
| 1.4 | Separate upload failure from bad file | Fixed | `ApasUploader.tsx` |
| 1.5 | Return focus after Add | Fixed | `ManualEntry.tsx` |
| 1.6 | Consistent mobile course rows | Fixed | `onboarding.css` |
| 2.1 | Save blank graduation target as blank | Fixed | `ProfileScreen.tsx` |
| 2.2 | Correct the defaults hint | Fixed | `ProfileScreen.tsx` |
| 2.3 | Generate graduation targets | Fixed | `ProfileScreen.tsx`, `lib/terms.ts` |
| 2.4 | Prefill name from sign-in | Fixed | `ProfileScreen.tsx` |
| 2.5 | Focus first invalid field | Fixed | `ProfileScreen.tsx` |
| 2.6 | Warn on a major not in the list | Fixed | `ProfileScreen.tsx` |
| 3.1 | Pause the step spinner | Fixed | `BuildingPlanScreen.tsx`, `ui/Display.tsx` |
| 3.2 | Subtitle matches the state | Fixed | `BuildingPlanScreen.tsx` |
| 3.3 | Back button on Step 3 | Fixed | `BuildingPlanScreen.tsx` |
| 3.4 | Heading inside the catalog panel | Fixed | `onboarding.css` |
| O.1 | One primary button per screen | Open | `ApasUploader.tsx`, `ui/` Dropzone |
| O.2 | One secondary button style | Open | `ApasUploader.tsx`, `ManualEntry.tsx` |
| O.3 | One validation pattern | Open | `BuildingPlanScreen.tsx` |
| O.4 | One loading pattern | Open | `CourseworkScreen.tsx` |
| O.5 | No duplicate Continue error | Open | `CourseworkScreen.tsx` |
| O.6 | One name for the upload | Open | `ImportChoice.tsx`, `ApasUploader.tsx`, `CourseworkScreen.tsx` |
| O.7 | Clearer parsed status | Open | `ApasUploader.tsx` |
| O.8 | No box in a box on Skip | Open | `CourseworkScreen.tsx` |
| O.9 | One action row on Step 3 | Open | `BuildingPlanScreen.tsx` |
| O.10 | Named steps | Open | `components/StepHeader.tsx` |
| O.11 | Logo does not reset the flow | Open | `app/layouts/OnboardingLayout.tsx` |
| O.12 | Redirect onboarded students | Open | `app/router.tsx` |
| O.13 | Restore Step 1 after reload | Open | `CourseworkScreen.tsx` |
| O.14 | Search hint and debounce | Open | `ManualEntry.tsx` |

Paths are under `frontend/src/screens/onboarding/` unless they start with `ui/`, `lib/` or `app/` (under `frontend/src/`).
