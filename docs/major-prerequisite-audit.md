# Prerequisite and liberal education audit: ten popular majors (2026-11-24)

Branch `data/major-prereq-audit`. This audit covers prerequisite chains and liberal education (LE) course picks for ten high-enrollment Twin Cities majors: Computer Science B.S., Mechanical Engineering B.M.E., Finance B.S.B., Neuroscience B.S., Psychology B.A., Biology B.S., Economics B.A., Marketing B.S.B., Electrical Engineering B.E.E. and Kinesiology B.S.

## Sources

| Source | What it gives | File |
| --- | --- | --- |
| UMN course catalog (umtc.catalog.prod.coursedog.com), retrieved 2026-11-23 | Course titles, credits, offering seasons, prerequisite prose, LE designations | `backend/data/catalog-exports/courses.2026-11-23.csv` |
| Schedule Builder section API (schedulebuilder.umn.edu), Fall 2026 and Spring 2027, retrieved 2026-11-25 UTC | The enrollment requirement registration actually enforces for every offered section (33,700 sections, 9,547 courses, 4,986 with a requirement) | `backend/data/catalog-exports/requisites.2026-11-25.csv`, from `scripts/export_requisites.py` |
| UMN class search (courses.umn.edu) | Section class numbers per subject and term, used only to enumerate sections | Not stored |
| Official program requirements and sample plans (sampleplan.umn.edu) | Which courses each major requires or schedules | Existing files in `backend/data/programs` and `backend/data/sample_plans` |

The catalog and registration sources disagree in places. Where they do, the reviewed tree follows the requirement registration enforces and keeps the catalog wording in a `note`.

## What was wrong

1. **Most prerequisites were never enforced.** Only text made entirely of course codes joined by one kind of connector became a tree. Across the ten majors, 923 of 1,378 referenced courses (67%) had text-only prerequisites, which warn but never order a plan. Only 20 of the majors' core courses had an enforced tree.
2. **A blank catalog field was read as "no prerequisites".** The course exporter keeps text only after a line-start `prereq:`. Prerequisites written mid-description (ECON 3024, MKTG 3011, CHEM 1082, BA 3051, EE 3951W) or held only by registration (NSCI 3101, BIOL 2003, ECON 3951, EEB 3408W, BMEN 3011, MATS 2001) came through blank. The planner treated these courses as having no prerequisites and the LE picker treated them as prerequisite-free.
3. **The bundled CSCI/MATH trees have errors.** "Placement test, or C- in [1151 or 1155]" was stored as placement and MATH 1151 and MATH 1155, which would force precalculus before calculus for anyone without a placement record. Several trees also hold subject-less codes such as `1572`.
4. **No concurrent registration.** Every prerequisite had to finish a term earlier. Labs (CHEM 1065/1066/1086/2085), PHYS 1302W with Calculus II, EE 2015 with linear algebra, FINA 4422 with FINA 4221 and ACCT 5101, and ECON 3012 with ECON 3011 were pushed a term too late.
5. **LE picks ignored enrollment restrictions.** The prerequisite-free LE pool included 410 honors (`H`) courses, freshman seminars that only first-year students may take, and 5xxx graduate courses. "Periodic" offerings ranked the same as courses offered every year.

## What changed

- `scripts/export_requisites.py` exports the enforced requirement per course and term from Schedule Builder (sequential, paused requests, no login).
- `app/services/requisites.py` resolves each course's prerequisites, most authoritative first:
  1. a hand-reviewed tree in `backend/data/prerequisites/reviewed.json`;
  2. the enforced registration requirement, when it parses completely;
  3. the catalog text, when it parses completely;
  4. otherwise text that warns and never blocks. A course that registration restricts is never treated as having no prerequisites.

  The parser now reads bare numbers in the course's own subject, `&`, "SUBJ [..]" brackets, "concurrent registration in", and a trailing minimum grade (kept as a review note). A required course missing from the catalog leaves the requirement as text, so a retired course can't block a plan forever.
- `reviewed.json` holds 202 hand-reviewed trees covering the core chains of the ten majors. Policy:
  - Only the standard course route is enforced.
  - Major, college, class-standing and minimum-grade rules are conditions that warn but never block.
  - Instructor-consent, graduate-standing and broad "or equivalent" escape hatches are left out of the tree and recorded in `note`.
  - Placement-test alternatives stay non-blocking, so MATH 1271 never forces precalculus.
  - Lecture/lab pairs that each require the other concurrently are enforced on the lab only. A two-way concurrent requirement can't be ordered, and a test rejects cycles.
- Prerequisite course nodes accept `"concurrent": true`, so the course may share a term with that prerequisite. This applies in the backend evaluator, the frontend move checks and the prerequisite display.
- `build_programs.py` and `import_catalog.py` both use the resolver (`--requisites`, `--reviewed`). Reviewed trees also replace the bundled SQLite rows they list, fixing the MATH trees above.
- The LE picker (`le_candidates`, `suggest_le_course`) skips honors courses, freshman seminars and 5xxx courses, and prefers courses offered every year. The tracker's double-dipper list ranks those courses last instead of hiding them.
- All 155 program files were rebuilt. Requirement groups are unchanged except Mechanical Engineering's: its catalog record lists one Chemistry I option by an unpublished course id, which a small sourced overlay (`scripts/program_overlays/052822207.json`) maps to CHEM 1071, the course the official sample plan and the enforced requirements of ME 3331 and MATS 2001 name. Mechanical Engineering still shows as unverified.
- Generator fixes found by the end-to-end check below:
  - Program equivalents no longer drop the `concurrent` flag.
  - Concurrent prerequisites are placed no earlier than the course they go with, so lectures and labs share a term when the load allows.
  - Class-standing conditions ("sophomore", "junior", "upper division", "senior", "60 credits") set the earliest term on the plan's credit load. They never block a course.
  - Requirement pools rank honors, freshman-seminar and Talented Youth Mathematics Program courses last, and skip a variant (an honors twin, for example) of a course already taken or planned.

## Results per major

Counts are for each program file's referenced courses. "Core" is the major's required courses, its sample plan's courses, and their prerequisite chains. "Trees" are prerequisite records the planner enforces (some carry review notes).

| Major | Courses | Trees before | Trees after | Text-only before | Text-only after | Core courses | Core trees before | Core trees after |
|---|---|---|---|---|---|---|---|---|
| Computer Science B.S. | 232 | 23 | 94 | 159 | 113 | 45 | 6 | 35 |
| Mechanical Engineering B.M.E. | 425 | 19 | 116 | 340 | 274 | 47 | 1 | 39 |
| Finance B.S.B. | 57 | 5 | 25 | 32 | 26 | 45 | 3 | 21 |
| Neuroscience B.S. | 148 | 6 | 52 | 90 | 64 | 53 | 2 | 38 |
| Psychology B.A. | 68 | 3 | 19 | 47 | 41 | 11 | 0 | 10 |
| Biology B.S. | 131 | 6 | 47 | 84 | 58 | 46 | 1 | 32 |
| Economics B.A. | 42 | 4 | 24 | 25 | 14 | 21 | 3 | 17 |
| Marketing B.S.B. | 47 | 3 | 20 | 25 | 21 | 40 | 3 | 16 |
| Electrical Engineering B.E.E. | 78 | 1 | 49 | 59 | 18 | 45 | 1 | 36 |
| Kinesiology B.S. | 151 | 0 | 22 | 62 | 52 | 35 | 0 | 12 |

Across the ten files: enforced trees went from 70 to 468, text-only from 923 to 681, and "no prerequisites" from 385 to 230. Those 155 courses had prerequisites the catalog text didn't show.

The core courses still without a tree are almost all restriction-only: "Carlson School student", "Kin major", "honors student", "CSE upper division", first-year experience courses, and placement-only math. These remain warnings because the planner can't check a student's college, major or standing.

## Chains by major (core route as now enforced)

- **Computer Science:** Calculus I (or placement) → CSCI 1133 with Calculus I concurrent → CSCI 1933 → CSCI 2021. CSCI 2011 (needs Calculus I) with 1933 → CSCI 2041 → CSCI 3081W. CSCI 1933 and 2011 → CSCI 4041. CSCI 2021 → CSCI 4061 → CSCI 4131. PHYS 1301W → PHYS 1302W with Calculus II concurrent.
- **Mechanical Engineering:** MATH 1371 → 1372 → MATH 2373/2374. PHYS 1301W with MATH 2374 concurrent → AEM 2021 → ME 3281. AEM 3031 (statics plus MATH 2374) → ME 3221 (with ME 2011 and MATS 2001) → ME 3222. CHEM 1061/1071 with CHEM 1065 and PHYS 1301W → ME 3331 → 3332 → 3333 → ME 4053 and 4054W. IE 3521 (needs MATH 1372) → ME 4031W.
- **Electrical Engineering:** EE 1301 → EE 2301 → EE 2361. PHYS 1302W and linear algebra (both concurrent allowed) → EE 2015 → EE 2115 → EE 3015 → EE 3025 → EE 4501 and 4541. EE 3015 and 3115 (concurrent) → EE 3101 → EE 3102 → EE 4951W.
- **Finance:** ACCT 2051, BA 2051, ECON 1101 and BA 2551 → FINA 3001 → FINA 4121, 4221 and 4321. FINA 4221 and ACCT 5101 (concurrent) → FINA 4422. FINA 4121 with FINA 4321 concurrent → FINA 4522. FINA 4422 and 4522 → FINA 4242W and 4329.
- **Marketing:** ECON 1101 → MKTG 3001 → MKTG 3041. MKTG 3001 and BA 2551 → MKTG 3011. MKTG 3011 and 3041 → MKTG 4051, 4061 and 4081W.
- **Economics:** ECON 1101 → 1102. ECON 1101, 1102 and MATH 1271 (or 1142) → ECON 3011 → 3012 (3011 concurrent allowed) → ECON 3023 → 3024 (3023 concurrent allowed). Registration then gates 4xxx electives on ECON 3012/3101 or 3024/3102. Capstone ECON 3951 needs ECON 3024 or 3102, an intro stats course, and STAT 3022 or 3032.
- **Neuroscience:** NSCI 2001 or 2101 → NSCI 3101 → NSCI 3102W and 4101. BIOL 1951 → BIOL 2003 → BIOL 4003 and 4004. CHEM 1061 → 1062 → 2301 → 2302 → BIOC 4331. CHEM 2301 → BIOC 3022.
- **Biology:** BIOL 1951 (with 1961 lab) → BIOL 2003 → BIOL 4003/4004 and GCD 3486. BIOL 4003 → GCD 4151. The chemistry chain is the same as neuroscience. EEB 3408W needs intro biology plus calculus.
- **Psychology:** PSY 1001 → PSY 3801 → PSY 3001W → PSY 3902W and 4521. PSY 1001 → the 3xxx distribution courses.
- **Kinesiology:** anatomy (KIN 3027 or ANAT) and the Kin major → KIN 3385 → KIN 4385. Physics plus anatomy → KIN 3112.

## End-to-end check

A dry-run plan was generated for a new first-year student (no coursework, 15 credits a term, graduating Spring 2030) in each of the ten majors, against a local SQLite catalog imported from the committed data (`courses.db`, the course snapshot, the registration requirements and `reviewed.json`). Every planned course was then re-checked against its resolved prerequisite tree.

- **Prerequisite order:** no violations in any of the ten plans.
- **LE picks:** no honors, freshman-seminar or 5xxx courses.
- **Removed by these changes:** these had appeared in the first run of this check:
  - MATH 1471 (Talented Youth Mathematics Program) in Finance and Psychology.
  - BA 2005H planned after BA 2005, and KIN 4001H.
  - ME 4094 (directed research, ME upper division) and EE 3102 in a first-year fall.
  - EE 4389W in a first-year spring.
  - A second first-semester chemistry course (CHEM 1061 after CHEM 1071) in Mechanical Engineering.
- **Now follows the official sample plans:**
  - Electrical Engineering: PHYS 1302W in year 1 spring with Calculus II; EE 2015 in year 2 fall; EE 3015, 3101 and 3115 together in year 3 fall.
  - Computer Science: PHYS 1302W in year 1 spring, beside MATH 1372.
  - Neuroscience: NSCI 2001, then 3101, then 3102W, then 4101 in successive terms.

Remaining issues seen in the check, outside prerequisite data:

- **Electrical Engineering, 15 credits a term:** EE 3102 and EE 4951W (senior design) don't fit. The greedy generator fills the last terms before the senior design chain reaches them, and reports `requirements_incomplete`. At UMN's typical 16 to 17 credits it fits.
- **Co-op courses:** CSE 4896 and 4996 have no stated prerequisite in either source, so they can land early when a major lists them as options.
- **Lab timing:** when a term is already full, a lab can land one term after its lecture (Mechanical Engineering: CHEM 1071 in year 1 spring, CHEM 1065 in year 2 fall).
- **3xxx LE courses early:** LE picks favor courses that cover two needs, which are often 3xxx courses open to any student, so some land in year 1.

### Every major

The same dry run was repeated for all 155 program files, re-checking each planned course against its prerequisites with the program's equivalent courses applied, as the planner does.

- **First run:** 150 majors clean. One real violation: in Computer Science B.A., CSCI 4271W was placed before CSCI 3081W. The program's "one writing-intensive course" menu (CSCI 3081W, 3921W, 4271W, ...) was treated as a set of interchangeable courses, so 4271W counted toward its own prerequisite.
- **Fix:** program equivalents now cover only variants of one course: honors or suffix twins and cross-listings (same number), or lower-division courses at one level (MATH 1271, 1371, 1571H). A course never counts toward its own prerequisite.
- **After the fix:** 0 prerequisite-order violations, 0 restricted LE picks and 0 errors across all 155. The fix added no new `requirements_incomplete` plans (60 before and after).

To repeat this for a new term: re-export the registration requirements, rebuild the program files, run the dry run, and hand-review only the majors it flags.

## Known limits

- Reviewed trees cover the ten majors' core chains only. Other courses use parsed registration or catalog text, or remain warnings.
- Registration requirements are term-specific. Re-export each term (`export_requisites.py --terms ...`) and rebuild.
- College, major, standing, honors and minimum-grade rules are not checked against the student; they appear as review warnings.
- The LE restriction filter uses the course number and title. It can't see seat reservations or restrictions stated only in a section note.
- `CatalogPrerequisiteEdge` rows (used for display of the bundled CSCI/MATH graph) are not rewritten when a reviewed tree replaces a SQLite row's prerequisites.
