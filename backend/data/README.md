# data

Catalog and program seed data. Separate from user data.

| Path | What it is |
| --- | --- |
| `courses.db` | Bundled course catalog export (CSCI and MATH, catalog version `unknown`). Source for `scripts/import_catalog.py`, which loads it (its rows win over the CSV) into the `catalog_*` database tables. Never edited; the app does not read it at runtime. |
| `catalog-exports/` | Dated public snapshots of every Twin Cities program (`programs.<date>.csv`) and course version (`courses.<date>.csv`). `courses.<date>.csv` is also merged by `scripts/import_catalog.py --csv` for every course outside `courses.db`; prerequisites from it are unverified text. `scripts/validate_programs.py` checks every program's courses against it. See [catalog-exports/README.md](catalog-exports/README.md). |
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
uv run python scripts/build_programs.py --programs data/catalog-exports/programs.<date>.csv --courses data/catalog-exports/courses.<date>.csv --output data/programs --replace
```

`build_programs.py` maps each undergraduate major's official revision conservatively. Structures v2 can express exactly become rules; free text, attribute-defined lists, credit caps, unresolved required courses and ambiguous nested lists become `review` rules; unresolved alternatives become a review branch. Each file's catalog term comes from its own revision date (for example 2026-09-08 is Fall 2026, 2027-01-19 is Spring 2027). Course facts come from the matching official course records. Prerequisite text becomes a tree only when it consists entirely of course codes joined by one kind of connector per bracket level; anything else is kept as a sourced free-text condition that never blocks placement but always raises `prerequisites_require_review`. No grade policy is inferred, so machine-mapped majors report grade checks as review.

Program rules stated only in prose need a reviewed overlay in `scripts/program_overlays/<officialProgramId>.json`. Computer Science B.S. (`019627107`) has one: the 23-credit technical elective total, 11 CSCI credits, the math-oriented requirement, at most two GDES/PDES courses, the writing-intensive requirement, the substitution waiver, restricted substitutions as review only, and the C- A-F grade policy from the CS&E Undergraduate Guide. It is the only file reviewed rule by rule; the others are machine-mapped and should be checked against APAS before students rely on them.

## Selecting and adding versions

Students explicitly choose a supported catalog term; the planner never applies a candidate year on its own and never combines files from different terms. To add a version, take a new dated snapshot, rebuild into a scratch directory, compare it with the current files by `officialProgramId`, review changed rules and overlays, then copy the new `<id>--<term>.json` files into `programs/` alongside the old ones. Existing plans keep their saved term until the student switches, and switching keeps their saved courses. Run `uv run pytest -q`; `tests/test_shipped_programs.py` checks that every file traces to its official revision, totals and course sources.
