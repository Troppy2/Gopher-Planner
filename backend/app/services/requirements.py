"""Pure v2 requirement evaluation: completed and projected progress, no Flask or database.

Evidence allocation is deterministic and greedy. Within a no-reuse ``all`` rule, specific
course rules claim evidence before alternatives and set-based quotas. Top-level groups claim
evidence in file order and reuse it only under one sourced sharing declaration covering every
group that uses the course. This is not a global optimizer; see the v2 contract.
"""
from dataclasses import dataclass, field

from app.services.summary import GRADE_POINTS

SATISFIED, UNSATISFIED, REVIEW = "satisfied", "unsatisfied", "needs_review"
NO_CREDIT_GRADES = {"F", "N", "W", "I"}
SEASON_ORDER = {"Spring": 0, "Summer": 1, "Fall": 2}


def term_key(term):
    if not term:
        return (0, -1)
    season, year = term.split()
    return int(year), SEASON_ORDER.get(season, 0)


@dataclass
class Outcome:
    status: str
    matched: list = field(default_factory=list)
    consumed: set = field(default_factory=set)
    missing: list = field(default_factory=list)
    details: list = field(default_factory=list)
    applied: list = field(default_factory=list)
    quantities: dict = field(default_factory=dict)


def _add_details(target, values):
    for value in values:
        if value not in target:
            target.append(value)


def qualify(attempts, policy, projected):
    """Return (state, attempt, detail) for the best attempt of one course code."""
    ranked = []
    for item in attempts:
        status, grade = item["status"], item.get("grade")
        if item["status"] != "done" and not projected:
            continue
        if status != "done":
            if policy is None:
                ranked.append((1, 0, term_key(item.get("term")), item, "No sourced grade policy; verify that this course counts"))
            else:
                threshold = f"a grade of {policy['minGrade']} or better" if policy["minGrade"] else "a passing grade"
                ranked.append((2, 0, term_key(item.get("term")), item, f"Assumes {item['code']} earns {threshold}"))
            continue
        if grade in NO_CREDIT_GRADES:
            ranked.append((0, 0, term_key(item.get("term")), item, f"{item['code']} earned {grade}, which does not qualify"))
        elif policy is None:
            ranked.append((1, 0, term_key(item.get("term")), item, "No sourced grade policy; verify that this course counts"))
        elif grade is None:
            if policy["minGrade"] is None and policy["allowS"]:
                ranked.append((3, 0, term_key(item.get("term")), item, None))
            else:
                ranked.append((1, 0, term_key(item.get("term")), item, f"The grade for {item['code']} is unknown; verify that it meets the grade requirement"))
        elif grade == "S":
            if policy["allowS"]:
                ranked.append((3, 0, term_key(item.get("term")), item, None))
            else:
                ranked.append((0, 0, term_key(item.get("term")), item, f"{item['code']} earned S, but this requirement needs a letter grade"))
        elif policy["minGrade"] is None or GRADE_POINTS[grade] >= GRADE_POINTS[policy["minGrade"]]:
            ranked.append((3, GRADE_POINTS[grade], term_key(item.get("term")), item, None))
        else:
            ranked.append((0, 0, term_key(item.get("term")), item, f"{item['code']} earned {grade}; this requirement needs {policy['minGrade']} or better"))
    if not ranked:
        return "none", None, None
    rank, _, _, item, detail = max(ranked, key=lambda value: value[:3])
    state = {3: "yes", 2: "yes", 1: "review", 0: "no"}[rank]
    return state, item, detail


class Evaluation:
    def __init__(self, program, attempts, *, projected, effects, trigger_codes):
        self.program = program
        self.projected = projected
        self.effects = effects
        self.trigger_codes = trigger_codes
        self.by_code = {}
        for item in attempts:
            if item["status"] == "done" or projected:
                self.by_code.setdefault(item["code"], []).append(item)
        self.outcomes = {}

    def candidate(self, code, available, policy):
        if code not in available:
            return "none", None, None
        return qualify(self.by_code[code], policy, self.projected)

    def run(self):
        used_by = {}
        declarations = [set(entry["groups"]) for entry in self.program.get("sharing", [])]
        for group in self.program["groups"]:
            gid = group["id"]
            available = {
                code for code in self.by_code
                if not used_by.get(code) or any(gid in declared and used_by[code] <= declared for declared in declarations)
            }
            outcome = self.node(group["rule"], available, group.get("gradePolicy"))
            outcome = self.waive(gid, outcome)
            self.outcomes[gid] = outcome
            for code in outcome.consumed:
                used_by.setdefault(code, set()).add(gid)
        return self.outcomes

    def waive(self, identity, outcome):
        effect = self.effects.get(identity)
        if effect and effect.get("satisfy"):
            adjustment = effect["adjustment"]
            codes = ", ".join(self.trigger_codes.get(adjustment, [])) or "the qualifying substitution"
            return Outcome(SATISFIED, [], set(), [], [f"Waived by {adjustment} because of {codes}"] + outcome.details,
                           [adjustment], outcome.quantities)
        return outcome

    def node(self, rule, available, policy):
        policy = rule.get("gradePolicy", policy)
        kind = rule["type"]
        outcome = getattr(self, f"rule_{kind}")(rule, available, policy)
        outcome = self.waive(rule["id"], outcome)
        self.outcomes[rule["id"]] = outcome
        return outcome

    def rule_course(self, rule, available, policy):
        code = rule["code"]
        state, _, detail = self.candidate(code, available, policy)
        details = [detail] if detail else []
        if state == "yes":
            return Outcome(SATISFIED, [code], {code}, [], details)
        if state == "review":
            return Outcome(REVIEW, [code], {code}, [], details)
        return Outcome(UNSATISFIED, [], set(), [code], details)

    def rule_review(self, rule, available, policy):
        return Outcome(REVIEW, details=[rule["message"]])

    def _caps(self, rule):
        caps = []
        for child in rule["children"]:
            if child["type"] == "count" and "maxCourses" in child:
                caps.append(child)
            elif child["type"] == "all":
                caps.extend(self._caps(child))
        return caps

    def _credits(self, code):
        return max(float(item["credits"]) for item in self.by_code[code])

    def rule_all(self, rule, available, policy):
        pool = set(available)
        for cap in self._caps(rule):
            capped = sorted((code for code in pool if code in self.program["courseSets"][cap["courseSet"]]["codes"]),
                            key=lambda code: (-self._credits(code), code))
            pool -= set(capped[cap["maxCourses"]:])
        order = {"course": 0, "any": 1, "all": 1, "review": 1, "credits": 2, "count": 2}
        children = sorted(enumerate(rule["children"]), key=lambda pair: (order[pair[1]["type"]], pair[0]))
        results = {}
        consumed = set()
        for index, child in children:
            results[index] = self.node(child, pool if rule["allowReuse"] else pool - consumed, policy)
            consumed |= results[index].consumed
        ordered = [results[index] for index in range(len(rule["children"]))]
        statuses = {result.status for result in ordered}
        status = UNSATISFIED if UNSATISFIED in statuses else REVIEW if REVIEW in statuses else SATISFIED
        matched, missing, details = [], [], []
        for result in ordered:
            matched.extend(code for code in result.matched if code not in matched)
            missing.extend(code for code in result.missing if code not in missing)
            _add_details(details, result.details)
        return Outcome(status, matched, consumed, missing, details)

    def rule_any(self, rule, available, policy):
        results = [self.node(child, available, policy) for child in rule["children"]]
        satisfied = [result for result in results if result.status == SATISFIED]
        if satisfied:
            chosen = max(satisfied, key=lambda result: len(result.matched))
            return Outcome(SATISFIED, chosen.matched, chosen.consumed, [], chosen.details)
        status = REVIEW if any(result.status == REVIEW for result in results) else UNSATISFIED
        chosen = max(results, key=lambda result: len(result.matched))
        details = []
        for result in results:
            if result.status == REVIEW or result is chosen:
                _add_details(details, result.details)
        # An incomplete alternative reports its progress but does not lock evidence away from later groups.
        return Outcome(status, chosen.matched, set(), chosen.missing, details)

    def _set_candidates(self, rule, available, policy):
        codes = self.program["courseSets"][rule["courseSet"]]["codes"]
        found = {"yes": [], "review": []}
        details = []
        for code in sorted(codes):
            state, _, detail = self.candidate(code, available, policy)
            if state in found:
                found[state].append(code)
                if detail:
                    details.append(detail)
        return found, details

    def rule_credits(self, rule, available, policy):
        required = rule["minCredits"]
        effect = self.effects.get(rule["id"])
        applied = []
        if effect and "reduceMinCredits" in effect:
            required -= effect["reduceMinCredits"]
            applied = [effect["adjustment"]]
        found, details = self._set_candidates(rule, available, policy)
        matched, total = [], 0.0
        for code in found["yes"]:
            if total >= required:
                break
            matched.append(code)
            total += self._credits(code)
        if total >= required:
            status = SATISFIED
        else:
            possible = total + sum(self._credits(code) for code in found["review"])
            status = REVIEW if possible >= required else UNSATISFIED
            matched.extend(found["review"])
        return Outcome(status, matched, set(matched), [], details, applied,
                       {"requiredCredits": required, "matchedCredits": total})

    def rule_count(self, rule, available, policy):
        found, details = self._set_candidates(rule, available, policy)
        quantities = {key: rule[key] for key in ("minCourses", "maxCourses") if key in rule}
        if "minCourses" not in rule:
            matched = found["yes"][:rule["maxCourses"]]
            quantities["matchedCourses"] = len(matched)
            return Outcome(SATISFIED, matched, set(), [], details, [], quantities)
        matched = found["yes"][:rule["minCourses"]]
        quantities["matchedCourses"] = len(matched)
        if len(matched) >= rule["minCourses"]:
            status = SATISFIED
        else:
            status = REVIEW if len(matched) + len(found["review"]) >= rule["minCourses"] else UNSATISFIED
            matched = matched + found["review"]
        return Outcome(status, matched, set(matched), [], details, [], quantities)


def _evaluate(program, attempts, projected):
    effects, trigger_codes = {}, {}
    active = None
    for _ in range(len(program["adjustments"]) + 1):
        evaluation = Evaluation(program, attempts, projected=projected, effects=effects, trigger_codes=trigger_codes)
        outcomes = evaluation.run()
        qualifying = {}
        for adjustment in program["adjustments"]:
            for trigger in adjustment["whenAnySatisfied"]:
                if outcomes[trigger].status == SATISFIED:
                    qualifying[adjustment["id"]] = outcomes[trigger].matched
                    break
        if active == set(qualifying):
            return outcomes
        active = set(qualifying)
        trigger_codes = qualifying
        effects = {}
        for adjustment in program["adjustments"]:
            if adjustment["id"] in qualifying:
                for effect in adjustment["effects"]:
                    effects[effect["targetId"]] = {**effect, "adjustment": adjustment["id"]}
    return outcomes


def _evidence(outcome):
    value = {"matchedCodes": list(outcome.matched), "missingCodes": list(outcome.missing),
             "appliedAdjustments": list(outcome.applied)}
    value.update(outcome.quantities)
    return value


def evaluate_program(program, attempts):
    """Evaluate qualifying ``done`` evidence and projected ``done``/``prog``/``plan`` evidence."""
    completed = _evaluate(program, attempts, projected=False)
    projected = _evaluate(program, attempts, projected=True)
    progress = []

    def visit(node, group_label, parent):
        label = node.get("label") or (node["code"] if node.get("type") == "course" else group_label)
        details = []
        _add_details(details, completed[node["id"]].details)
        _add_details(details, projected[node["id"]].details)
        progress.append({
            "id": node["id"], "label": label, "parentId": parent,
            "type": node.get("type", "group"), "category": node.get("category"),
            "completedStatus": completed[node["id"]].status, "projectedStatus": projected[node["id"]].status,
            "completedEvidence": _evidence(completed[node["id"]]), "projectedEvidence": _evidence(projected[node["id"]]),
            "details": details,
        })
        if "rule" in node:
            visit(node["rule"], group_label, node["id"])
        for child in node.get("children", []):
            visit(child, group_label, node["id"])

    for group in program["groups"]:
        visit(group, group["label"], None)
    group_statuses = [projected[group["id"]].status for group in program["groups"]]
    group_statuses += [completed[group["id"]].status for group in program["groups"]]
    warnings = []
    if UNSATISFIED in (projected[group["id"]].status for group in program["groups"]):
        warnings.append("requirements_incomplete")
    if REVIEW in group_statuses:
        warnings.append("requirements_need_review")
    return {"requirementProgress": progress, "warnings": warnings}
