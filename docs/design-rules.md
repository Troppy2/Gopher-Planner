# Gopher Planner Frontend Design Document

This document defines the visual language, layout rules, responsive behavior, and screen requirements for Gopher Planner. Use it as the source brief for the Figma design and frontend implementation.

## Product Direction

Gopher Planner is a calm, focused academic planning workspace for University of Minnesota students and advisors. It turns a student's APAS or manually entered coursework into a personalized four-year plan.

The interface should feel:

- Academic, trustworthy, and distinctly University of Minnesota-inspired.
- Clear enough for students to understand quickly during stressful planning periods.
- Dense enough for advisors to scan requirements, progress, and course paths.
- Personal without feeling like a social network.
- Modern and polished, using restrained glass surfaces over a warm ivory foundation.

Avoid a marketing-heavy landing page inside the authenticated product. The dashboard is the primary product experience.

## Design Principles

1. **Progress is always visible.** GPA, credits, degree completion, current classes, and next actions should be easy to find.
2. **Planning should feel reversible.** Users can explore course paths without committing changes to their saved plan.
3. **Complexity appears on demand.** Show the useful summary first, then expose prerequisites, professor history, grades, and requirement details through drawers, panels, or expanded states.
4. **Use consistent academic language.** Prefer terms such as `completed`, `in progress`, `planned`, `prerequisite`, `concurrent requirement`, and `remaining credits`.
5. **Every state is designed.** Include loading, empty, error, unavailable, completed, locked, and unsaved states in the Figma file.

## Visual Foundation

### Color Palette

Use the three primary colors as the foundation. Do not use maroon for large body surfaces or gold for large blocks of text.

| Token | Color | Value | Use |
| --- | --- | --- | --- |
| `color-maroon` | Maroon | `#7A0019` | Primary actions, active navigation, headings, focus accents |
| `color-gold` | Gold | `#FFCC33` | Progress highlights, attention states, selected indicators, secondary accents |
| `color-ivory` | Ivory | `#E6E0D2` | Main page background, warm neutral surfaces |
| `color-ink` | Ink | `#201A1B` | Primary text and icons |
| `color-muted` | Muted ink | `#625A5C` | Secondary text, metadata, helper text |
| `color-surface` | Frosted white | `rgba(255, 255, 255, 0.72)` | Glass panels and cards |
| `color-border` | Soft border | `rgba(32, 26, 27, 0.14)` | Dividers, card outlines, field boundaries |
| `color-success` | Success green | `#237A57` | Completed requirements and valid states |
| `color-warning` | Warning amber | `#A86400` | Missing prerequisites, attention states |
| `color-danger` | Error red | `#B42318` | Validation and destructive errors |

The palette should read as maroon, gold, and ivory with enough ink contrast to remain accessible. Do not introduce a purple-first or dark-mode-first visual direction.

### Texture and Surfaces

- Main background: smooth ivory with a very subtle paper-like tonal variation.
- Cards and panels: frosted glass surfaces with a soft translucent fill, 1px border, and restrained backdrop blur.
- Use blur to create hierarchy, not decoration. Important text and controls must remain high contrast if blur is unavailable.
- Keep borders visible in light and low-contrast environments.
- Avoid excessive shadows. Prefer a soft shadow such as `0 12px 30px rgba(32, 26, 27, 0.08)` for elevated panels.

### Typography

Use an expressive serif or humanist display face for major page titles, paired with a highly legible sans-serif for interface text. Keep the typography hierarchy compact inside dashboards and data-heavy screens.

Suggested roles:

- Display: distinctive serif or humanist font for product name and page titles.
- Interface: readable sans-serif for controls, labels, data, and navigation.
- Numeric emphasis: interface font with tabular numerals for GPA, credits, and percentages.

Rules:

- Do not use oversized hero typography inside the application.
- Keep letter spacing at `0`.
- Use sentence case for labels and buttons.
- Never rely on color alone to communicate requirement status.

### Spacing and Shape

Use a 4px base spacing unit:

- `space-1`: 4px
- `space-2`: 8px
- `space-3`: 12px
- `space-4`: 16px
- `space-6`: 24px
- `space-8`: 32px
- `space-12`: 48px

Use 8px or less for standard card and input corner radii. Pills are reserved for compact statuses, filters, and progress labels, not large text buttons.

## Layout System

### Desktop

Target desktop canvas: 1440px wide, with the design remaining usable from 1024px upward.

- Persistent left navigation rail: approximately 240px wide.
- Main content: centered, with a maximum width of approximately 1280px.
- Page gutters: 32px on desktop and 24px on smaller laptops.
- Use a 12-column grid for dashboard and catalog layouts.
- Keep primary content above the fold: summary metrics, search, and the user's next academic action.

The supplied mockup uses a dashboard shell with a large content area and a compact navigation bar. Preserve that information hierarchy, but use a persistent desktop rail when there is enough horizontal space.

### Mobile

Target mobile canvases: 390px and 430px wide.

- Replace the desktop rail with a fixed bottom navigation bar.
- Use four primary navigation items: Dashboard, Flow chart, Course catalog, and Settings.
- Keep the bar within the safe area and give it a solid or sufficiently opaque surface.
- Page padding: 16px.
- Use a single-column layout.
- Stack metric cards horizontally only when each card remains readable; otherwise use a two-column grid.
- Convert wide tables into stacked course rows or horizontally scrollable sections with visible affordances.
- Place search and primary actions near the top of the page.
- Do not hide critical progress information behind a desktop-only hover interaction.

### Breakpoints

Use behavior-based breakpoints rather than designing only for device names:

- Small mobile: below 360px
- Mobile: 360px to 767px
- Tablet: 768px to 1023px
- Desktop: 1024px and above

At tablet widths, the navigation can become a compact rail or top navigation depending on available space. The bottom navigation is required for mobile.

## Navigation and App Shell

### Primary Navigation

The four destinations are:

1. Dashboard
2. Flow chart
3. Course catalog
4. Settings

Use familiar icons with text labels on desktop and icon-plus-label items on mobile. Use a tooltip for unfamiliar desktop rail icons. The active destination should use maroon and a clear selected background or indicator; do not communicate active state through color alone.

### Global Header

The authenticated header contains:

- Current page title or breadcrumb.
- Global course search trigger where appropriate.
- Notification or system status area only if the product needs it.
- User avatar or account control.

On mobile, keep the header short and move secondary actions into an overflow menu.

## Screen Specifications

## 1. Dashboard

### Purpose

Give the user an immediate view of academic progress and a clear route to the next planning action.

### Desktop composition

1. Page header with `Dashboard`, a short personalized greeting, and account control.
2. Course search bar with placeholder text such as `Search courses, professors, or course codes`.
3. Summary metric row:
   - GPA
   - Credits completed / total credits
   - Degree completion percentage
4. Current classes panel.
5. Upcoming or planned classes panel.
6. User details panel with major, standing, graduation target, and preferred credit load.
7. A compact progress or next-step panel, such as `Review your next semester`.

### Mobile composition

- Header and search first.
- Metrics in a two-column grid, with degree progress spanning the full width when needed.
- Current classes and future classes as stacked cards.
- User details below academic progress.
- Keep the next action visible before the user reaches the bottom navigation.

### Metric card rules

- Label first, value second, supporting context third.
- Use tabular numerals for GPA, credits, and percentages.
- Degree completion requires both a percentage and a progress bar or ring with a text label.
- Use `N/A` or `Not available` for missing values rather than a blank card.

## 2. Flow Chart

### Purpose

Show the current classes and the possible course paths needed to complete the selected major.

### Desktop composition

- A top toolbar with selected major, academic year or term filter, zoom controls, and a reset view control.
- A large canvas showing courses as nodes connected by prerequisite or recommended-path lines.
- A side detail panel that opens when a course is selected.
- A legend for completed, in progress, planned, available, and blocked courses.

### Course node states

- Completed: success indicator and muted body.
- In progress: gold indicator and active outline.
- Planned: maroon outline with planned-term label.
- Available: neutral surface with clear action.
- Blocked: warning indicator plus the missing prerequisite or restriction.

### Mobile composition

- Use a horizontally and vertically pannable canvas with a visible minimap or `Fit plan` control.
- Keep zoom controls reachable but compact.
- Open course details in a bottom sheet rather than a permanent side panel.
- Provide a list view toggle for users who cannot comfortably navigate the graph.
- Ensure the flow chart is not the only way to understand the plan.

### Interaction rules

- Selecting a node highlights its prerequisite and dependent paths.
- A course detail view shows credits, prerequisites, concurrent requirements, offered terms, historical professors, and links to Gopher Grades and Rate My Professors when available.
- Moving or adding a course must show prerequisite conflicts before saving.
- Unsaved changes require a visible save or discard action.

## 3. Course Catalog

### Purpose

Let users search, filter, compare, and inspect courses independently of their current plan.

### Desktop composition

- Prominent search field.
- Filter controls for subject, level, credits, term, requirement type, and availability.
- Results list or table with course code, title, credits, offering information, and requirement status.
- Course detail drawer or page with description, prerequisites, concurrent requirements, professors, grade information, and add-to-plan action.

### Mobile composition

- Search field at the top.
- Filter button opens a full-screen or bottom-sheet filter panel.
- Results become stacked cards with course code and title as the strongest hierarchy.
- Keep `View details` and `Add to plan` as separate actions to prevent accidental changes.

### Search states

- Initial: explain what can be searched without adding marketing copy.
- Loading: use stable skeleton rows that do not shift the page.
- Results: show result count and active filters.
- No results: suggest clearing filters or trying a broader course code.
- Error: explain that catalog data could not be loaded and provide retry.

## 4. Settings

### Purpose

Let users update the information used to personalize their plan.

### Editable fields

- Name
- Major or degree program
- Grade standing
- Career goals
- Maximum or preferred credit workload
- Desired graduation date, if collected during onboarding

### Desktop composition

- Group fields into `Profile`, `Academic goals`, and `Planning preferences`.
- Use a two-column form only where labels and validation remain clear.
- Keep save state visible: `Saved`, `Unsaved changes`, `Saving`, and `Could not save`.

### Mobile composition

- Use a single-column form.
- Keep section headings sticky only when they do not cover fields.
- Use a full-width save action near the end of the form and preserve the user's position after validation errors.

## Onboarding

Onboarding is a one-time setup flow. It should be skippable where data is optional and resumable if the user leaves before completion.

### Step 1: Coursework import choice

Present three equally understandable options:

1. **Upload APAS** - Upload a transcript or APAS PDF for parsing.
2. **Enter courses manually** - Search for courses and mark them completed or in progress.
3. **Skip for now** - Start with a basic four-year plan based on profile information.

The upload screen must include accepted file types, file size guidance, upload progress, parsing status, and a manual correction step when text cannot be extracted. Scanned PDFs may contain no selectable text, so the UI must support an OCR or manual-entry fallback instead of treating the upload as a silent failure.

### Step 2: Profile setup

Collect:

- Name
- Grade standing
- Major or degree program
- Career goals

If maximum credit workload or graduation date is needed for plan generation, collect it here or make the missing value explicit before generating the plan.

### Onboarding behavior

- Show a step indicator, such as `1 of 2`.
- Allow Back, Continue, Skip, and Finish actions where applicable.
- Validate one step at a time.
- Do not discard uploaded or manually entered coursework when the user navigates backward.
- End with a plan-generation status screen and a clear route to the Dashboard.

## Login and Public Entry Screen

The login screen should be a focused entry point, not a full marketing page.

### Required content

- Gopher Planner name and visual identity.
- Slogan: `Tired of Looking? Try Gopher Planner!`
- Google sign-in action restricted to eligible University of Minnesota accounts.
- Short project description.
- GitHub link.
- Terms and privacy links.

### Layout

Desktop can use a two-zone composition: brand and slogan on one side, login action and supporting links on the other. Mobile should stack the slogan, sign-in action, and legal links in that order.

Use maroon as the primary action color, ivory as the base, and gold as a small accent. Keep the sign-in action obvious and avoid placing legal text inside a visually confusing card.

## Shared Components

Design these as reusable components with desktop, mobile, loading, error, and disabled variants:

- App shell and navigation
- Page header
- Search input
- Metric card
- Progress bar or progress ring
- Course card
- Course table row
- Status badge
- Filter control
- Select and combobox
- Modal, drawer, and bottom sheet
- Toast or inline alert
- Empty state
- Skeleton loader
- File upload dropzone
- Flow-chart course node and connector
- Save/discard action bar

Buttons should use icons where a familiar symbol exists, include accessible names, and avoid rounded text pills for actions that could use a standard icon.

## Accessibility Rules

- Meet WCAG 2.2 AA contrast targets for text, controls, and focus indicators.
- Provide a visible keyboard focus state using maroon or a high-contrast outline.
- Every icon-only button needs an accessible name and tooltip where appropriate.
- Do not rely on maroon, gold, or red alone to indicate course status.
- Preserve logical heading order and landmarks.
- Make dialogs, drawers, bottom sheets, and the flow-chart canvas keyboard usable.
- Provide a text/list alternative for the visual flow chart.
- Respect reduced-motion preferences.
- Keep touch targets at least 44px by 44px.

## Motion and Feedback

Use a small number of meaningful transitions:

- Fade and slight rise when dashboard sections load.
- Progress animation when a plan is generated or updated.
- Smooth drawer and bottom-sheet transitions.
- Subtle highlight when a flow-chart path is selected.

Do not animate large data tables continuously or make important academic information move unexpectedly. Every async action needs a visible loading, success, or error state.

## Figma Deliverables

Create the following frames and variants:

- Login: desktop and mobile.
- Onboarding coursework choice: desktop and mobile.
- Onboarding profile form: desktop and mobile.
- Dashboard: desktop at 1440px, tablet, and mobile at 390px.
- Flow chart: desktop canvas, selected course drawer, mobile canvas, and mobile bottom sheet.
- Course catalog: desktop results, filters open, no results, and mobile results.
- Settings: desktop form, unsaved state, validation error, and mobile form.
- Shared navigation, buttons, inputs, cards, badges, dialogs, skeletons, and alerts.

Use Auto Layout, named color and type variables, component properties for state, and documented spacing. Include annotations for responsive behavior rather than creating disconnected one-off screens.

## Acceptance Checklist

- The four authenticated destinations are represented on desktop and mobile.
- Dashboard shows GPA, credits, degree completion, course search, current classes, future classes, and user details.
- Flow chart communicates course paths and has a non-graph fallback on mobile.
- Course catalog supports searching, filtering, details, and adding a course to a plan.
- Settings supports all requested profile and planning fields.
- Onboarding supports APAS upload, manual entry, and skip.
- Upload failures caused by image-only PDFs have an explicit recovery path.
- Login includes the slogan, sign-in action, GitHub, terms, privacy, and project details.
- Loading, empty, error, disabled, selected, and unsaved states are designed.
- Desktop and mobile layouts do not overlap, clip, or hide required text.
- Keyboard focus, contrast, touch targets, and reduced motion are addressed.