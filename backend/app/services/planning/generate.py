"""Deterministic, requirement-aware plan generation.

Groups are filled in category priority, then file order. Inside a group the engine repeatedly
re-evaluates projected progress and adds one course (with its prerequisite closure) for the first
unsatisfied machine-checkable rule. ``any`` rules choose whole branches by existing qualifying
evidence, then a preferred branch (``preferred: true`` or "(Preferred)" in the label), then fewer
additional credits including missing prerequisites, then source order. Course pools rank options by
how many open rules they count toward, the program's home subject, missing prerequisite credits,
course level, then code; when a branch cannot be scheduled the
group's placements are rolled back and the next complete branch is tried. This is a bounded
greedy search, not a global optimizer: an incomplete result is not proof that no schedule exists.

Liberal education: sample-plan slots are filled first; after the program's requirements are placed,
any core area, theme (4 of 5, Race, Power, and Justice required) or writing intensive course still
open is filled from a candidate pool, one course at a time, preferring the course that covers the
most open needs. Designations carried by required major courses count, so they are never doubled.

Free electives: until the plan reaches the degree's credit total (going over is fine), courses are
added from the major's own elective pools (sets of 8+ courses under a credits rule or a "choose at
least 2" rule), then from the liberal education pool. Courses named in specific rules, choose-one
equivalents, graduate courses and repeats of a course already taken or planned are never added.
"""
import re

from app.services.liberal_ed import open_needs
from app.services.metadata import home_subject

from app.services.planning.eligibility import placement_check
from app.services.planning.sample import sample_terms
from app.services.planning.terms import term_index
from app.services.requirements import evaluate_program

CATEGORY_PRIORITY = {"Major core": 0, "Math and stats": 1, "Elective": 2, "Liberal ed": 3}
STATUS_WARNINGS = {"unknown": "program_requirements_unavailable", "unavailable": "program_version_unavailable",
                   "unconfirmed": "program_version_unconfirmed"}
MAX_STEPS = 400
# Upper bound on gap-filling courses: 7 core + 4 themes + 4 writing intensive.
MAX_LE_FILLS = 15
# Elective pools smaller than this are usually lists of equivalent alternatives, not electives.
MIN_ELECTIVE_POOL = 8


def program_codes(program):
    """Every course code a program names, in rules or course sets."""
    codes = set()

    def walk(node):
        if node["type"] == "course":
            codes.add(node["code"])
        for child in node.get("children", []):
            walk(child)

    for group in program["groups"]:
        walk(group["rule"])
    for course_set in program["courseSets"].values():
        codes.update(course_set["codes"])
    return codes


class Planner:
    def __init__(self, program, coursework, metadata, terms, credit_load, *, le_suggest=None, le_coverage=frozenset(),
                 le_pool=(), le_designations=None, le_rules=None):
        self.program = program
        self.coursework = coursework
        self.metadata = metadata
        self.terms = terms
        self.credit_load = credit_load
        self.done = {item["code"] for item in coursework if item["status"] == "done"}
        self.in_progress = {item["code"] for item in coursework if item["status"] == "prog"}
        self.locked = self.done | self.in_progress
        self.planned = {}
        self.loads = [0.0] * len(terms)
        for item in coursework:
            # Courses already registered for a future term use up that term's credit load.
            if item["status"] == "prog" and item.get("term") in terms:
                self.loads[terms.index(item["term"])] += float(item["credits"])
        self.warnings = set()
        self.blocked_reasons = set()
        self.home_subject = self._home_subject()
        self.metadata = dict(metadata)
        self.slots = {}
        self.le_suggest = le_suggest
        self.le_coverage = set(le_coverage)
        # Pool courses never come from a subject the major uses: a pool course there is likely an
        # equivalent of a major course under another number (a second Calculus I, an honors twin).
        program_subjects = {code.split(" ")[0] for code in program_codes(program)} if program else set()
        self.le_pool = [item for item in (le_pool or ()) if item["code"].split(" ")[0] not in program_subjects]
        self.le_designations = {code: set(names) for code, names in (le_designations or {}).items()}
        self.le_designations.update({item["code"]: set(item["designations"]) for item in self.le_pool})
        self.le_rules = le_rules

    def _home_subject(self):
        """Most common subject among courses named directly in the program's rules."""
        return home_subject(self.program)

    def prerequisite_cost(self, code):
        """Credits of unplanned prerequisites ``code`` would pull in; large when it cannot be scheduled."""
        if code not in self.metadata:
            return 999.0
        visiting_blocked = set(self.blocked_reasons)
        order = self.closure(code, frozenset())
        self.blocked_reasons = visiting_blocked  # ranking must not record warnings
        if order is None:
            return 999.0
        return sum(self.credits(item) for item in order if item != code and item in self.metadata)

    def option_key(self, code):
        number = code.split(" ")[-1]
        level = int(number[0]) if number[:1].isdigit() else 9
        return (code not in self.program.get("preferredCourses", ()), code.split(" ")[0] != self.home_subject,
                self.prerequisite_cost(code), level, code)

    @staticmethod
    def preferred(node):
        return bool(node.get("preferred")) or "(preferred)" in node.get("label", "").lower()

    def credits(self, code):
        return float(self.metadata[code]["minimumCredits"])

    def attempts(self):
        planned = [{"code": code, "credits": self.credits(code), "status": "plan", "grade": None, "term": self.terms[index]}
                   for code, index in self.planned.items()]
        return list(self.coursework) + planned

    def evaluate(self):
        return evaluate_program(self.program, self.attempts())

    # Placement with prerequisite closure.

    def satisfied_now(self, code):
        return code in self.locked or code in self.planned

    def closure(self, code, visiting):
        """Ordered unplanned courses needed before ``code``, plus ``code``; None when impossible."""
        record = self.metadata.get(code)
        if record is None or record.get("blockedReason") or (record.get("prerequisites") or {}).get("state") == "unknown":
            self.blocked_reasons.add("course_metadata_unavailable")
            return None
        if code in visiting:
            return None
        visiting = visiting | {code}
        expression = (record.get("prerequisites") or {}).get("expression")
        needed = self.expression_closure(expression, visiting) if expression else []
        if needed is None:
            return None
        return [item for item in needed if item != code] + [code]

    def expression_closure(self, node, visiting):
        kind = node.get("type")
        if kind == "course":
            code = node.get("course_code")
            return [] if self.satisfied_now(code) else self.closure(code, visiting)
        if kind == "all_of":
            ordered = []
            for child in node.get("requirements") or []:
                part = self.expression_closure(child, visiting)
                if part is None:
                    return None
                ordered.extend(item for item in part if item not in ordered)
            return ordered
        if kind == "any_of":
            options = []
            for index, child in enumerate(node.get("requirements") or []):
                part = self.expression_closure(child, visiting)
                if part is not None:
                    options.append((len(part), index, part))
            return min(options)[2] if options else None
        return []

    def place(self, code, start=0):
        """Place ``code`` (no earlier than ``start``) and its closure at the earliest feasible terms, or change nothing."""
        order = self.closure(code, frozenset())
        if order is None:
            return False
        added = []
        for item in order:
            if item in self.planned or item in self.locked:
                continue
            position = self.earliest(item, start if item == code else 0)
            if position is None:
                for undo in added:
                    self.loads[self.planned.pop(undo)] -= self.credits(undo)
                return False
            self.planned[item] = position
            self.loads[position] += self.credits(item)
            added.append(item)
        return True

    def earliest(self, code, start=0):
        record = self.metadata[code]
        credits = self.credits(code)
        last_reason = None
        for position, term in enumerate(self.terms):
            if position < start:
                continue
            if self.loads[position] + credits > self.credit_load:
                continue
            check = placement_check(record, term, position, done=self.done, in_progress=self.in_progress, planned=self.planned)
            if check.ok:
                self.warnings.update(check.warnings)
                return position
            last_reason = check.reason
        if last_reason == "course_metadata_unavailable":
            self.blocked_reasons.add(last_reason)
        return None

    # Requirement-driven selection.

    def additional_credits(self, node, progress):
        if node["type"] == "course":
            code = node["code"]
            if self.satisfied_now(code):
                return 0.0
            return self.credits(code) if code in self.metadata else 999.0
        if node["type"] == "credits":
            evidence = progress[node["id"]]["projectedEvidence"]
            return max(0.0, evidence["requiredCredits"] - evidence["matchedCredits"])
        if node["type"] == "count":
            evidence = progress[node["id"]]["projectedEvidence"]
            return max(0, evidence.get("minCourses", 0) - evidence["matchedCourses"]) * 3.0
        parts = [self.additional_credits(child, progress) for child in node.get("children", [])]
        if not parts:
            return 0.0
        if node["type"] == "any":
            return min(parts)
        # Children of a reuse-permitted rule overlap, so the largest part is the honest lower bound.
        return max(parts) if node.get("allowReuse") else sum(parts)

    def covered(self, node, progress):
        """Satisfied, or unresolved only because existing evidence awaits verification."""
        entry = progress[node["id"]]
        return entry["projectedStatus"] == "satisfied" or (
            entry["projectedStatus"] == "needs_review" and bool(entry["projectedEvidence"]["matchedCodes"]))

    def choose(self, node, progress, infeasible, path, siblings=()):
        kind = node["type"]
        status = progress[node["id"]]["projectedStatus"]
        if status == "satisfied" or kind == "review":
            return None
        # A review-only alternative must not stop planning a machine-checkable branch, but
        # evidence that merely awaits verification must not trigger extra courses.
        if status == "needs_review" and (kind not in {"any", "all"} or self.covered(node, progress)):
            return None
        if kind == "any" and any(self.covered(child, progress) for child in node["children"]):
            return None
        if kind == "course":
            code = node["code"]
            if code in infeasible["codes"] or self.satisfied_now(code):
                return None
            return code, path
        if kind == "all":
            quotas = [child for child in node["children"] if child["type"] in {"credits", "count"}
                      and progress[child["id"]]["projectedStatus"] == "unsatisfied"] if node["allowReuse"] else []
            for child in node["children"]:
                found = self.choose(child, progress, infeasible, path, quotas)
                if found:
                    return found
            return None
        if kind == "any":
            order = {child["id"]: index for index, child in enumerate(node["children"])}
            branches = [child for child in node["children"] if child["id"] not in infeasible["branches"]]
            branches.sort(key=lambda child: (-len(progress[child["id"]]["projectedEvidence"]["matchedCodes"]),
                                             not self.preferred(child), self.additional_credits(child, progress),
                                             order[child["id"]]))
            for child in branches:
                found = self.choose(child, progress, infeasible, path + [child["id"]])
                if found:
                    return found
            return None
        if kind in {"credits", "count"}:
            if kind == "count" and "minCourses" not in node:
                return None
            sets = self.program["courseSets"]
            peers = [peer for peer in siblings if peer["id"] != node["id"]] + [node]
            candidates = [code for code in sets[node["courseSet"]]["codes"]
                          if not self.satisfied_now(code) and code not in infeasible["codes"]]
            candidates.sort(key=lambda code: (-sum(code in sets[peer["courseSet"]]["codes"] for peer in peers),
                                              *self.option_key(code)))
            return (candidates[0], path) if candidates else None
        return None

    def fill_group(self, group):
        infeasible = {"codes": set(), "branches": set()}
        snapshot = (dict(self.planned), list(self.loads))
        for _ in range(MAX_STEPS):
            progress = {item["id"]: item for item in self.evaluate()["requirementProgress"]}
            found = self.choose(group, progress, infeasible, [])
            if found is None:
                return
            code, path = found
            if self.place(code):
                continue
            if path:
                infeasible["branches"].add(path[-1])
                self.planned, self.loads = dict(snapshot[0]), list(snapshot[1])
            else:
                infeasible["codes"].add(code)

    # Sample-plan seeding.

    def contributes(self, code):
        """True when ``code`` would count toward a rule whose ancestors are all still unsatisfied."""
        progress = {item["id"]: item for item in self.evaluate()["requirementProgress"]}
        sets = self.program["courseSets"]

        def walk(node):
            if progress.get(node["id"], {}).get("projectedStatus") == "satisfied" or node["type"] == "review":
                return False
            if node["type"] == "course":
                return node["code"] == code
            if node["type"] in {"credits", "count"}:
                # A max-only count is a cap, never a reason to add a course.
                return code in sets[node["courseSet"]]["codes"] and ("minCredits" in node or "minCourses" in node)
            return any(walk(child) for child in node.get("children", []))

        return any(walk(group["rule"]) for group in self.program["groups"])

    def referenced(self, code):
        sets = self.program["courseSets"]

        def walk(node):
            if node["type"] == "course":
                return node["code"] == code
            if node["type"] in {"credits", "count"}:
                return code in sets[node["courseSet"]]["codes"]
            return any(walk(child) for child in node.get("children", []))

        return any(walk(group["rule"]) for group in self.program["groups"])

    def seed(self, plan, graduation):
        mapping = sample_terms(graduation, start=self.terms[0] if self.terms else None)
        if not plan or not mapping or not self.terms:
            return
        first = term_index(self.terms[0])
        for term in plan["terms"]:
            key = (term["year"], term["season"])
            if term["season"] == "Summer":
                key = (term["year"] + 1, "Fall")
            target = mapping.get(key)
            if target is None:
                continue
            past = term_index(target) < first
            start = self.terms.index(target) if target in self.terms else (0 if past else len(self.terms) - 1)
            for item in term["items"]:
                if item["kind"] == "le":
                    self.seed_le(item, start, target)
                elif item["kind"] in {"course", "choice"} and not past:
                    self.seed_course(item, start)

    def seed_course(self, item, start):
        codes = [code for code in item["codes"] if code in self.metadata]
        if not codes or any(self.satisfied_now(code) for code in item["codes"]):
            return
        for code in codes:
            if self.referenced(code) and not self.contributes(code):
                continue
            if self.place(code, start):
                return

    def seed_le(self, item, start, target):
        missing = [category for category in item["categories"] if category not in self.le_coverage]
        if not missing or self.le_suggest is None:
            return
        season_term = target if target in self.terms else self.terms[start]
        while missing:
            suggestion = self.le_suggest(missing, season_term, self.locked | set(self.planned))
            if not suggestion:
                return
            code, record, covered = suggestion
            if code in self.locked or code in self.planned or not set(covered).intersection(missing):
                return
            self.metadata[code] = record
            if not self.place(code, start):
                return
            self.slots[code] = item.get("label") or ", ".join(item["categories"])
            self.le_coverage |= set(covered)
            missing = [category for category in missing if category not in self.le_coverage]

    def le_state(self):
        """Designations and writing intensive count across finished, in-progress and planned courses."""
        codes = self.locked | set(self.planned)
        covered = set(self.le_coverage)
        for code in codes:
            covered |= self.le_designations.get(code, set())
        writing = sum("Writing Intensive" in self.le_designations.get(code, ()) for code in codes)
        return covered, writing

    def fill_le_gaps(self):
        """Add pool courses for liberal education needs still open, best combined coverage first."""
        if not self.le_rules or not self.le_pool:
            return
        for _ in range(MAX_LE_FILLS):
            covered, writing = self.le_state()
            needs = open_needs(self.le_rules, covered, writing)
            if not needs:
                return
            if not self.place_le_need(needs):
                break
        # Something is still open and nothing more fits (full terms, or no eligible course).
        if open_needs(self.le_rules, *self.le_state()):
            self.warnings.add("liberal_ed_unplanned")

    def place_le_need(self, needs):
        taken = self.locked | set(self.planned)

        def level(code):
            number = code.split(" ")[-1]
            return int(number[0]) if number[:1].isdigit() else 9

        for _, wanted in needs:
            candidates = [item for item in self.le_pool if item["code"] not in taken and item["designations"] & wanted]
            candidates.sort(key=lambda item: (-sum(bool(item["designations"] & group) for _, group in needs),
                                              level(item["code"]), item["code"]))
            for item in candidates:
                self.metadata.setdefault(item["code"], item["record"])
                if self.place(item["code"]):
                    self.slots[item["code"]] = ", ".join(label for label, group in needs if item["designations"] & group)
                    return True
        return False

    def elective_candidates(self):
        """Major elective-pool courses that are safe to add as free electives, best first.

        Only upper-division (3xxx-4xxx) courses in the program's home subject, from pools of 8+ courses
        under a credits rule or a "choose at least 2" rule: large option lists for math, science or
        intro sequences hold equivalent alternatives (Calculus I/II variants, honors twins), and adding
        one of those as an "elective" would duplicate a course the student already has.
        """
        specific, usable = set(), set()

        def walk(node):
            if node["type"] == "course":
                specific.add(node["code"])
            elif node["type"] in {"credits", "count"}:
                codes = self.program["courseSets"][node["courseSet"]]["codes"]
                electives = node["type"] == "credits" or node.get("minCourses", 2) >= 2
                if electives and len(codes) >= MIN_ELECTIVE_POOL:
                    usable.update(codes)
            for child in node.get("children", []):
                walk(child)

        for group in self.program["groups"]:
            walk(group["rule"])

        def level(code):
            number = code.split(" ")[-1]
            return int(number[0]) if number[:1].isdigit() else 9

        codes = [code for code in usable - specific if code in self.metadata and 3 <= level(code) <= 4
                 and code.split(" ")[0] == self.home_subject]
        return sorted(codes, key=self.option_key)

    @staticmethod
    def base_code(code):
        """A course without its letter suffix: CSCI 4041H and CSCI 4041W are both CSCI 4041."""
        subject, _, number = code.partition(" ")
        return f"{subject} {re.sub(r'[A-Z]+$', '', number)}"

    @staticmethod
    def title_key(record):
        """A course title for spotting repeats, ignoring case, punctuation and an "Honors" marker."""
        title = (record or {}).get("title") or ""
        title = re.sub(r"\bhonors?\b", " ", title.lower())
        return re.sub(r"[^a-z0-9]+", " ", title).strip()

    def fill_electives(self, needed):
        """Add courses until ``needed`` more credits are planned (the last one may go over).

        Upper-division major electives start in the second half of the plan, then move back to a
        quarter of the way in only if more room is needed, never into the first semesters; liberal
        education pool courses (mostly introductory) may go in any term.
        """
        if needed <= 0:
            return
        taken_titles = {self.title_key(self.metadata.get(code)) for code in self.locked | set(self.planned)} - {""}
        taken_numbers = {self.base_code(code) for code in self.locked | set(self.planned)}
        added = 0.0
        majors = self.elective_candidates()
        pool = [item["code"] for item in self.le_pool]
        half, quarter = len(self.terms) // 2, max(1, len(self.terms) // 4)
        passes = [(majors, half), (majors, quarter), (pool, 0)]
        for candidates, start in passes:
            for code in candidates:
                if added >= needed:
                    return
                if code in self.planned or code in self.locked:
                    continue
                if code not in self.metadata:
                    record = next((item["record"] for item in self.le_pool if item["code"] == code), None)
                    if record is None:
                        continue
                    self.metadata[code] = record
                title = self.title_key(self.metadata[code])
                if (title and title in taken_titles) or self.base_code(code) in taken_numbers:
                    continue
                before = set(self.planned)
                if self.place(code, start):
                    for new in set(self.planned) - before:
                        added += self.credits(new)
                        taken_titles.add(self.title_key(self.metadata.get(new)))
                        taken_numbers.add(self.base_code(new))

    def run(self):
        ordered = sorted(enumerate(self.program["groups"]),
                         key=lambda pair: (CATEGORY_PRIORITY.get(pair[1]["category"], 9), pair[0]))
        for _, group in ordered:
            group_node = {**group, "type": "all", "allowReuse": False, "children": [group["rule"]]}
            self.fill_group(group_node)


def generate_plan(program, *, coursework, metadata, terms, credit_load, base_credits=0, status="ok", sample=None,
                  graduation=None, le_suggest=None, le_coverage=frozenset(), le_pool=(), le_designations=None, le_rules=None):
    if status != "ok" or program is None:
        return {"placements": [], "warnings": [STATUS_WARNINGS.get(status, "program_requirements_unavailable")],
                "requirementProgress": []}
    planner = Planner(program, coursework, metadata, terms, credit_load, le_suggest=le_suggest, le_coverage=le_coverage,
                      le_pool=le_pool, le_designations=le_designations, le_rules=le_rules)
    planner.seed(sample, graduation)
    planner.run()
    planner.fill_le_gaps()
    in_progress_credits = sum(float(item["credits"]) for item in coursework if item["status"] == "prog")
    planned_credits = sum(planner.credits(code) for code in planner.planned)
    planner.fill_electives(float(program["totalCredits"]) - (base_credits + in_progress_credits + planned_credits))
    evaluation = planner.evaluate()
    warnings = set(planner.warnings) | set(evaluation["warnings"])
    if "requirements_incomplete" in warnings and planner.blocked_reasons:
        warnings |= planner.blocked_reasons
    projected = base_credits + in_progress_credits + sum(planner.credits(code) for code in planner.planned)
    if projected < float(program["totalCredits"]):
        warnings.add("graduation_target_unreachable")
    placements = sorted(({"code": code, "term": terms[index], **({"slot": planner.slots[code]} if code in planner.slots else {})}
                         for code, index in planner.planned.items()),
                        key=lambda item: (terms.index(item["term"]), item["code"]))
    return {"placements": placements, "warnings": sorted(warnings), "requirementProgress": evaluation["requirementProgress"],
            "electiveCredits": max(0.0, float(program["totalCredits"]) - projected),
            "metadata": {code: planner.metadata[code] for code in planner.slots}}
