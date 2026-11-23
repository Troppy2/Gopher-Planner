---
name: simple-design
description: Use when designing, building, or refactoring a frontend or React interface. Applies the user's product-minded visual system, interaction standards, responsive rules, and component architecture.
---

# Simple Design

Design the real product workflow first. Make the interface feel intentional, useful, and specific to its domain. Avoid generic dashboard or AI-generated UI patterns.

## Before Coding

- Read the project's existing design system, routes, components, tokens, and instructions.
- Identify the user, their main task, and the information they need first.
- Choose a clear visual direction that fits the product. State it in one sentence.
- Define the content hierarchy, primary action, secondary actions, and important states before styling.
- Extend existing patterns before inventing new ones. Adapt to the project instead of copying this skill's example values.
- Use real product content and representative states, not placeholder filler.

## Visual Principles

- Use purposeful typography. Prefer a distinctive type family when the project does not already have one.
- Build a palette with semantic roles: positive, caution, danger, and informational. Check contrast instead of choosing colors by taste alone.
- Avoid purple-on-white defaults, one-note palettes, excessive dark mode, and decorative gradient blobs.
- Use cards only for repeated items, dialogs, or genuinely framed tools. Do not put cards inside cards.
- Keep page sections unframed and full-width where possible. Keep rectangular surfaces lightly rounded, usually 8px or less unless the design system says otherwise.
- Use icons for familiar actions and icon-plus-text for commands that need explanation. Use the project's icon library and provide labels or tooltips for unfamiliar icons.
- Make controls visually communicate their state. Do not use inert chips that look like tabs or decorative stat tiles that look interactive.
- Do not build a marketing hero when the user needs the application. Put the useful workflow in the first viewport.
- Do not add visible instructional paragraphs to explain obvious controls. Make the interface self-evident through hierarchy, labels, affordances, and feedback.
- Use meaningful motion for entry, progress, and state changes. Avoid animation on every element and respect reduced-motion preferences.
- Use relevant images or visual assets when they reveal the product, place, object, or state. Do not use dark, blurred, or generic stock imagery as a substitute for product clarity.

## React Architecture

- Let route pages coordinate data loading, page-level state, navigation, and loading/error/empty states.
- Let reusable components own presentation and local interaction. Keep them focused on one visual or behavioral responsibility.
- Put reusable behavior in hooks. Put API access, shared types, parsing, and domain utilities in the project's established library locations.
- Keep server data, URL state, persisted preferences, and temporary UI state separate. Store state at the lowest common owner that needs it.
- Derive values during render when possible. Use effects for synchronization with external systems, subscriptions, timers, and browser APIs, not for ordinary derived state.
- Do not add global state, context, memoization, or a new dependency without a real ownership or performance reason.
- Do not add `useMemo` or `useCallback` by habit. Follow the project's React Compiler and state-management conventions.
- Use transitions or deferred values when they improve a demonstrated expensive interaction, not as decoration.
- Keep data fetching and mutation boundaries obvious. Give every async workflow loading, success, empty, error, retry, and disabled behavior where applicable.
- Prefer composition over giant components and prop objects that hide unrelated responsibilities.

## Layout And Responsive Design

- Design desktop and mobile as first-class layouts, not as a desktop page squeezed into a phone.
- Establish stable dimensions for boards, grids, toolbars, tiles, buttons, and media so text or state changes do not move the layout.
- Keep touch targets at least 44px where practical.
- Reserve space for fixed navigation, players, sheets, and safe-area insets. Hidden fixed elements must not retain pointer events.
- Use `min-width: 0` on flexible grid and flex children that contain long content. Prefer `minmax(0, 1fr)` for constrained tracks.
- Prevent horizontal overflow from long titles, code, math, tables, and generated content. Use wrapping or an intentional local scroll region.
- Do not use viewport width as a substitute for responsive behavior. Account for touch devices, zoom, orientation, and container constraints.
- Use `dvh` for mobile-height workspaces. Do not rely on `100vh` when browser chrome affects the viewport.
- Keep navigation available on immersive screens. Put back navigation in the page header when a floating dock would cover the work surface.
- Use CSS media queries and shared responsive hooks consistently so markup and styling cannot disagree.

## Content And Interaction

- Use semantic HTML and visible hierarchy. Headings, labels, and actions should make sense without color.
- Keep primary actions obvious and secondary actions quiet. Make destructive actions explicit and distinguish reversible from irreversible choices.
- Provide useful empty states, progress feedback, recovery paths, and confirmation only where the consequence warrants it.
- Prefer inline errors for local form problems and toasts for brief global feedback. Do not show both for the same event.
- Preserve user input during loading and failure whenever possible.
- Render user-authored or model-generated Markdown, code, math, charts, and diagrams through the project's trusted renderers. Never execute generated code or HTML.
- Treat generated visuals as bounded declarative data. Validate specs, lazy-load heavy renderers, show a pending state while streaming, and show a readable fallback when rendering fails.
- Keep onboarding and tours short, target-driven, dismissible, and safe when targets are missing, hidden, or changed by an action.
- Support keyboard focus, keyboard operation, screen readers, reduced motion, and readable contrast.

## Styling

- Use the project's token system for color, spacing, type, radius, shadow, and motion before adding a new value.
- Keep stylesheet ownership clear: global tokens in the base layer, layout primitives in the layout layer, reusable component styles with components, and route-only styles with pages.
- Do not add new component-specific rules to a legacy global stylesheet when the project has a better owning stylesheet.
- Keep selectors narrow enough to avoid accidental cascade fights. Check import order and computed styles when a rule appears correct but does not win.
- Prefer a small, coherent spacing scale over many nearly identical values.
- Use one namespace for each materially different component. Do not make two players or docks share classes whose layouts evolve independently.

## Validation

After implementation:

1. Run the narrowest relevant tests, typecheck, lint, or build.
2. Check the real UI at a desktop viewport and a narrow mobile viewport.
3. Check loading, empty, error, long-content, disabled, and success states.
4. Check horizontal overflow, fixed-element clearance, touch targets, focus rings, and keyboard behavior.
5. Use screenshots and computed-style or hit-test checks for layout claims that are easy to get wrong by inspection.
6. Verify generated content and visual renderers with valid, streaming, malformed, and unsupported input.
7. Separate pre-existing failures from regressions and report both clearly.
