# data

Catalog and program seed data. Separate from user data.

| Path | What it is |
| --- | --- |
| `courses.db` | Bundled course catalog export (CSCI and MATH, catalog version `unknown`). Source for `scripts/import_catalog.py`, which loads it (its rows win over the CSV) into the `catalog_*` database tables. Never edited; the app does not read it at runtime. |
| `catalog-exports/` | Dated public snapshots of every Twin Cities program (`programs.<date>.csv`) and course version (`courses.<date>.csv`). `courses.<date>.csv` is also merged by `scripts/import_catalog.py --csv` for every course outside `courses.db`. `requisites.<date>.csv` holds the enrollment requirement registration enforces for each offered course, per term, from Schedule Builder. `scripts/validate_programs.py` checks every program's courses against it. See [catalog-exports/README.md](catalog-exports/README.md). |
| `sample_plans/` | Per-program official four-year sample plans built from `catalog-exports/sample-plans.2026-11-23.csv`. Used to seed generation before requirement filling; labels identify liberal education suggestions. Free electives are reported as credits and are not placed. |
| `prerequisites/reviewed.json` | Hand-reviewed prerequisite trees for the core courses of ten popular majors. They win over every other prerequisite source, including `courses.db`. See [docs/major-prerequisite-audit.md](../../docs/major-prerequisite-audit.md). |
| `programs/` | Versioned planner requirement files in the v2 format, one per undergraduate major and catalog term, plus `mapping-report.csv`. |

## v2 program files

The binding contract is [docs/specs/program-requirements-v2.md](../../docs/specs/program-requirements-v2.md). In short, each file `<id>--<catalog-term-slug>.json` holds:

- `schemaVersion: 2`, `id`, `name` (the profile major string), optional `officialName`, `officialProgramId`, `catalogTerm`, `totalCredits` (degree credits, not program-only credits).
- `source` text plus `sources`: every rule, course set, adjustment and supplemental course record names a source key with an official URL, retrieval date and section.
- `groups`: requirement trees built from `course`, `all` (with `allowReuse`), `any`, `credits`, `count` and `review` rules. A `review` rule is a known obligation the planner cannot verify; it is never treated as satisfied.
- `courseSets`, `sharing` (explicit, non-transitive reuse between top-level groups) and `adjustments` (sourced one-time credit reductions or waivers).
- `courseMetadata`: title, credit bounds, offered seasons and prerequisites for referenced courses, all for the file's own catalog term. `offered: null` means unknown, not every term. `prerequisites: null` means unknown and blocks automatic scheduling; `{"expression": null}` means the official record lists none.
- Optional `catalogCompatibility`: verified catalog releases that may override supplemental facts. The bundled catalog's `unknown` version never qualifies.

The loader validates every file in the directory on first use and caches it in memory. A malformed file, a name that does not match `<id>--<term>`, or two files claiming the same major and term fail every lookup loudly instead of silently picking one.

## How the shipped files were produced

From `backend`:

```powershell
uv run python scripts/export_programs.py --output data/catalog-exports/programs.<date>.csv
uv run python scripts/export_courses.py --output data/catalog-exports/courses.<date>.csv --from-date 2026-09-08 --to-date 2027-12-31
uv run python scripts/export_requisites.py --output data/catalog-exports/requisites.<date>.csv --terms 1269,1273 --courses data/catalog-exports/courses.<date>.csv
uv run python scripts/build_programs.py --programs data/catalog-exports/programs.<date>.csv --courses data/catalog-exports/courses.<date>.csv --requisites data/catalog-exports/requisites.<date>.csv --output data/programs --replace
```

`build_programs.py` maps each undergraduate major's official revision conservatively. Structures v2 can express exactly become rules; free text, attribute-defined lists, credit caps, unresolved required courses and ambiguous nested lists become `review` rules; unresolved alternatives become a review branch. Each file's catalog term comes from its own revision date (for example 2026-09-08 is Fall 2026, 2027-01-19 is Spring 2027). Course facts come from the matching official course records. Each course's prerequisites come from `app/services/requisites.py`: a hand-reviewed tree from `prerequisites/reviewed.json`, else the enforced registration requirement, else the catalog text. Text becomes a tree only when every token is a course code (a bare number means the course's own subject), a connector, a bracket, a "concurrent registration in" marker or a trailing minimum grade, with one kind of connector per bracket level, and only when every required course exists in the snapshot. Anything else is kept as a sourced free-text condition that never blocks placement but always raises `prerequisites_require_review`. A course whose catalog text is blank but whose registration enforces a requirement keeps that requirement as text, so it is never treated as having no prerequisites. Course nodes marked `concurrent` may be planned in the same term. No grade policy is inferred, so machine-mapped majors report grade checks as review.

Program rules stated only in prose need a reviewed overlay in `scripts/program_overlays/<officialProgramId>.json`. Computer Science B.S. (`019627107`) has one: the 23-credit technical elective total, 11 CSCI credits, the math-oriented requirement, at most two GDES/PDES courses, the writing-intensive requirement, the substitution waiver, restricted substitutions as review only, and the C- A-F grade policy from the CS&E Undergraduate Guide. It is the only file reviewed rule by rule; the others are machine-mapped and should be checked against APAS before students rely on them.

## Selecting and adding versions

Students explicitly choose a supported catalog term; the planner never applies a candidate year on its own and never combines files from different terms. To add a version, take a new dated snapshot, rebuild into a scratch directory, compare it with the current files by `officialProgramId`, review changed rules and overlays, then copy the new `<id>--<term>.json` files into `programs/` alongside the old ones. Existing plans keep their saved term until the student switches, and switching keeps their saved courses. Run `uv run pytest -q`; `tests/test_shipped_programs.py` checks that every file traces to its official revision, totals and course sources.

## Sample plans and full course snapshot

`catalog-exports/courses.2026-11-23.csv` includes descriptions and liberal education designations, also merged onto reviewed CSCI and MATH rows during import:

```powershell
uv run python scripts/import_catalog.py --csv data/catalog-exports/courses.2026-11-23.csv --requisites data/catalog-exports/requisites.2026-11-25.csv
uv run python scripts/export_sample_plans.py --output data/catalog-exports/sample-plans.2026-11-23.csv
uv run python scripts/build_sample_plans.py --sample-plans data/catalog-exports/sample-plans.2026-11-23.csv
```

The sample snapshot contains rows from all 161 public pages; 155 pages match programs. The exporter handles heading and paragraph term labels, merged cells, and optional Offered columns. It caches public HTML with `--source-cache <directory>` and retries rate-limited requests. Explicit slug aliases cover confirmed name differences only. Six pages remain unmatched: arts education, business analytics, business-economics emphasis, educational psychology, public/nonprofit management, and user experience design. No degree equivalence is inferred for these pages.

Sample plans are suggestions, not additional authoritative degree rules. Graduation targets map their four years onto calendar terms. Existing coursework covers LE categories; generation suggests prerequisite-free catalog courses for missing categories, skipping honors (`H`) courses, freshman seminars and 5xxx courses, and preferring courses offered every year. Moves and swaps retain slot labels. Free electives are reported as credits and are not placed. The sample sources are not catalog-version-specific, so students must review the draft against their APAS and advisor guidance.

## Liberal education rules

`liberal_ed/umn-tc.json` holds the Twin Cities liberal education requirements the tracker evaluates, with the official pages and retrieval dates in `sources`:

- **Diversified core:** one course in each of 7 areas.
- **Designated themes:** 4 of the 5. Race, Power, and Justice in the United States is required for students admitted Fall 2021 or later. Its former name, Diversity and Social Justice in the United States, still appears on 165 catalog courses and counts toward it.
- **Writing:** first-year writing (WRIT 1301, WRIT 1401, or an equivalent) and 4 writing intensive courses, 2 of them upper division (3xxx or higher) and 1 of those in the major.

A course can carry one core, one theme, and writing intensive at the same time, so it counts toward each kind once and never has to be split between two cores or two themes. Course designations come from the catalog's `le_attributes`. Older "... Core" and "... Theme" designations from the previous curriculum are not counted.

The tracker is an estimate. A parsed APAS audit takes precedence: categories it marks complete count even without a matching course (AP or transfer credit), core categories it does not list are shown as not required, and a category the catalog says is complete but the audit does not is shown as needing review. "In the major" for writing intensive means the course is listed by the student's program or shares its home subject. Edit the rules file only from official sources, and update `sources` when you do.
