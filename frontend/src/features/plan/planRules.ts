import type { Course, Plan, Profile, Requirement, TermId } from "@/api/types";

export const season = (term: TermId) => term.split(" ")[0];
export const sumCredits = (list: Course[]) => list.reduce((a, c) => a + c.credits, 0);

/** Index of the first term after the current one. */
export const firstFutureIndex = (plan: Pick<Plan, "terms" | "currentTerm">) => plan.terms.indexOf(plan.currentTerm) + 1;

/** Index of the graduation term, never earlier than the first future term. */
export function lastPlanIndex(plan: Pick<Plan, "terms" | "currentTerm">, profile?: Pick<Profile, "graduationTarget">) {
  const g = profile ? plan.terms.indexOf(profile.graduationTarget) : -1;
  const first = firstFutureIndex(plan);
  return g < first ? Math.max(first, plan.terms.length - 1) : g;
}

/** Credits already earned plus everything in progress or planned. */
export const projectedCredits = (base: number, courses: Course[]) =>
  base + sumCredits(courses.filter((c) => c.status === "prog" || c.status === "plan"));

/**
 * A course can be placed in a term when it's available, offered that season,
 * and each prerequisite is finished, in progress, or planned in an earlier term.
 */
export function eligible(course: Course, termIdx: number, courses: Course[], terms: TermId[]) {
  if (course.status !== "avail") return false;
  if (!course.offered.includes(season(terms[termIdx]) as Course["offered"][number])) return false;
  return course.prereqs.every((code) => {
    const p = courses.find((x) => x.code === code);
    if (!p) return true; // not tracked in this program
    if (p.status === "done" || p.status === "prog") return true;
    return p.status === "plan" && p.term !== null && terms.indexOf(p.term) < termIdx;
  });
}

/** Prerequisites that aren't completed, in progress, or planned yet. */
export const missingPrereqs = (course: Course, courses: Course[]) =>
  course.prereqs.filter((code) => {
    const p = courses.find((x) => x.code === code);
    return p && (p.status === "avail" || p.status === "block");
  });

/** Earliest term in the plan window where the course fits, or null with the reason. */
export function targetTerm(course: Course, courses: Course[], plan: Plan, profile?: Profile) {
  const last = lastPlanIndex(plan, profile);
  for (let i = firstFutureIndex(plan); i <= last; i++) {
    if (eligible(course, i, courses, plan.terms)) return { term: plan.terms[i], missing: [] as string[] };
  }
  return { term: null, missing: missingPrereqs(course, courses) };
}

const PRIORITY: Record<Requirement, number> = { "Major core": 0, "Math and stats": 1, Elective: 2, "Liberal ed": 3 };

/** Greedy fill: each future term up to the credit load, required courses first, stop at the credit goal. */
export function buildPlan(plan: Plan, courses: Course[], profile: Profile, goal: number): Course[] {
  const next = courses.map((c) => (c.status === "plan" ? { ...c, status: "avail" as const, term: null } : { ...c }));
  const last = lastPlanIndex(plan, profile);
  for (let i = firstFutureIndex(plan); i <= last; i++) {
    let credits = sumCredits(next.filter((c) => c.term === plan.terms[i] && c.status === "plan"));
    const candidates = next
      .filter((c) => eligible(c, i, next, plan.terms))
      .sort((a, b) => PRIORITY[a.requirement] - PRIORITY[b.requirement] || a.code.localeCompare(b.code));
    for (const c of candidates) {
      if (projectedCredits(plan.baseCredits, next) >= goal) return next;
      if (credits + c.credits > profile.creditLoad) continue;
      c.status = "plan";
      c.term = plan.terms[i];
      credits += c.credits;
    }
  }
  return next;
}
