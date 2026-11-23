import type { CatalogCourse, Course, Plan, PrerequisiteExpression, Profile, TermId } from "@/api/types";

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

/** Course codes in a prerequisite tree, for display only. */
export function treeCodes(node: PrerequisiteExpression | null | undefined): string[] {
  if (!node) return [];
  if (node.type === "course" && typeof node.course_code === "string") return [node.course_code.toUpperCase()];
  const children = (node as { requirements?: PrerequisiteExpression[] }).requirements ?? [];
  return [...new Set(children.flatMap(treeCodes))];
}

const LOCK_UNKNOWN = "Prerequisite information for this course isn't available from the catalog, so it can't be scheduled automatically. Ask your advisor before planning it.";

/** A catalog search result as a plan course outside the program: an available elective, or blocked when prerequisites are unknown. */
export function catalogToPlanCourse(course: CatalogCourse): Course {
  const record = course.prerequisites;
  const known = !!record && (record.status === "none" || (record.status === "found" && !!record.requirements));
  const tree = known ? record!.requirements : null;
  return {
    code: course.code, title: course.title, credits: course.minimumCredits, status: known ? "avail" : "block",
    requirement: "Elective", offered: course.offered, prereqs: treeCodes(tree), concurrent: [], professors: [], term: null,
    prerequisiteTree: tree, metadataSource: "catalog", metadataWarnings: ["catalog_version_unverified"],
    ...(known ? {} : { lockReason: LOCK_UNKNOWN }),
  };
}

/** True when the prerequisite is finished, in progress, or planned in a strictly earlier term. */
function satisfied(code: string, termIdx: number, courses: Course[], terms: TermId[]) {
  const p = courses.find((x) => x.code === code);
  if (!p) return false;
  if (p.status === "done" || p.status === "prog") return true;
  return p.status === "plan" && p.term !== null && terms.indexOf(p.term) < termIdx;
}

function treeMet(node: PrerequisiteExpression, termIdx: number, courses: Course[], terms: TermId[]): boolean {
  if (node.type === "course") return satisfied(String(node.course_code).toUpperCase(), termIdx, courses, terms);
  const children = (node as { requirements?: PrerequisiteExpression[] }).requirements ?? [];
  if (node.type === "all_of") return children.every((child) => treeMet(child, termIdx, courses, terms));
  if (node.type === "any_of") return children.some((child) => treeMet(child, termIdx, courses, terms));
  return true; // free-text conditions stay nonblocking; the server flags them for review
}

/**
 * A course can be placed in a term when it's available, offered that season, and its prerequisite
 * tree is met by finished, in-progress, or strictly earlier planned courses. The server re-validates.
 */
export function eligible(course: Course, termIdx: number, courses: Course[], terms: TermId[]) {
  if (course.status !== "avail") return false;
  if (course.offered.length && !course.offered.includes(season(terms[termIdx]) as Course["offered"][number])) return false;
  if (course.prerequisiteTree !== undefined) {
    return course.prerequisiteTree === null || treeMet(course.prerequisiteTree, termIdx, courses, terms);
  }
  return course.prereqs.every((code) => !courses.some((x) => x.code === code) || satisfied(code, termIdx, courses, terms));
}

/** Prerequisites that aren't completed, in progress, or planned yet. */
export const missingPrereqs = (course: Course, courses: Course[]) =>
  course.prereqs.filter((code) => {
    const p = courses.find((x) => x.code === code);
    return !p || p.status === "avail" || p.status === "block";
  });

/** Earliest term in the plan window where the course fits, or null with the reason. */
export function targetTerm(course: Course, courses: Course[], plan: Plan, profile?: Profile) {
  const last = lastPlanIndex(plan, profile);
  for (let i = firstFutureIndex(plan); i <= last; i++) {
    if (eligible(course, i, courses, plan.terms)) return { term: plan.terms[i], missing: [] as string[] };
  }
  return { term: null, missing: missingPrereqs(course, courses) };
}
