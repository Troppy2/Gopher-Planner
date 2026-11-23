# UMN Twin Cities program snapshots

`programs.2026-11-22.csv` contains all 880 program revisions advertised by the public [Twin Cities program catalog](https://umtc.catalog.prod.coursedog.com/programs) during this export. It includes undergraduate, graduate and professional programs, majors, minors, certificates, and other listed program types. It does not claim coverage of other UMN campuses or discontinued/hidden programs.

The export uses the public catalog's own filters, catalog ID and selection dates, discovered afresh from its published page. No login, token, Supabase connection or catalog SQLite write is used. The public request requires the catalog Origin and `x-requested-with: catalog` headers. Requests are paginated in unique revision-ID order; missing pages or duplicate revisions fail the export.

## Refresh each semester

From `backend`, choose a new snapshot filename:

```powershell
uv run python scripts/export_programs.py --output data/catalog-exports/programs.2027-01-15.csv
```

Use the actual snapshot date in the filename. Existing files are preserved. The command rediscovers the website's current catalog and filters, collects every advertised record, and prints the row count and source selection window. Keep old snapshots for comparison. Nothing runs automatically or changes the application's supported program files.

## Columns and provenance

| Columns | Meaning |
| --- | --- |
| `program_id`, `revision_id`, `code` | Stable source program identity, exact revision identity, and source code. Join by `program_id`; use `revision_id` and effective dates to select a version. |
| `name`, `campus`, `career`, `program_type`, `degree`, `college` | Official identifying fields. Blank source fields stay blank; types and careers are not guessed from names. |
| `effective_start_date`, `effective_end_date` | The source revision's dates. A blank end date means the source supplies none. Future-dated revisions remain explicit. |
| `degree_credits_min`, `degree_credits_max` | Degree credit totals, kept separate from program-only credit totals. Missing values stay blank. |
| `program_credits_min`, `program_credits_max` | Program-only credit bounds. |
| `description_json`, `departments_json` | JSON-encoded original source description and departments. |
| `requirements_json` | Original nested Coursedog requisite object, including all alternatives, bounds, notes, admission sections and sub-plan sections. No flattening or academic interpretation. |
| `requirement_levels_json` | Original requirement-section labels and notes, including obligations outside course lists. |
| `academic_metadata_json` | Source custom fields, excluding administrative contact, budget, proposal and program-assessment fields. Unknown academic field keys are retained. |
| `source_url`, `source_catalog_id`, `source_window_start`, `source_window_end`, `retrieved_at_utc` | Official page and exact extraction context. The source window is not a program's catalog term. |
| `academic_content_sha256` | Fingerprint of the captured row excluding retrieval timestamp. Changes in academic content, revision identity or source catalog/window change this hash. Compare source context before calling a difference a curriculum change. |

For this snapshot the site selected catalog `QEPaNgPjyzEkVlRYv42S` with window `2027-09-07` through `2032-12-15`. These are the site's literal published selection values, not inferred academic years. Individual rows retain their actual effective dates. For example, Computer Science B.S. revision `019627107-2026-09-08` has 120 degree credits and 78 to 80 program credits.

All 880 saved rows have distinct program and revision IDs, nonempty names, and JSON-parseable requisite objects. Fourteen records have no source career and 55 have no source program type. Those gaps are retained. Object presence does not establish that every rule is machine-checkable or academically verified.

## Read and compare safely

The CSV is UTF-8 with a BOM. JSON columns preserve nested structure and escape Unicode without changing decoded source text. Some fields exceed spreadsheet cell limits; use a CSV/JSON reader for application ingestion rather than saving the file back through Excel.

```python
import csv
import json

csv.field_size_limit(100_000_000)
with open("data/catalog-exports/programs.2026-11-22.csv", encoding="utf-8-sig", newline="") as source:
    programs = list(csv.DictReader(source))

requirements = json.loads(programs[0]["requirements_json"])
```

Compare snapshots by `program_id`; distinguish added/removed programs, changed revisions, and changed hashes. Inspect the actual changed fields and rules before updating versioned planner data. Preserve both snapshots and never merge requirements from different revisions.

Course references inside the native trees are Coursedog course identifiers, not invented equivalencies. They need resolution against matching official course records. The supplied course CSV contains 14,156 Twin Cities courses but does not expose these internal identifiers or an explicit catalog-term column. The [course catalog](https://umtc.catalog.prod.coursedog.com/courses) and public [Schedule Builder](https://schedulebuilder.umn.edu/) provide additional identity and term-specific evidence.

This is a source snapshot, not the validated planner v2 schema. Admission, degree and integrated-program sections remain distinct in the native source; consumers must not apply an integrated master's requirement to every undergraduate student. Semantic mapping, academic review and the P0 loader/evaluator acceptance tests remain required before enabling generation for every major.
