import type { CourseworkEntry, TermId } from "@/api/types";
import type { ManualCourse } from "./onboarding.store";

/** Manual onboarding entries in the coursework contract: completed rows have an unknown term. */
export function toCourseworkEntries(manual: ManualCourse[], current: TermId): CourseworkEntry[] {
  return manual.map((course) => ({
    code: course.code,
    title: course.title,
    credits: course.credits,
    status: course.status,
    term: course.status === "prog" ? current : null,
    grade: null,
  }));
}
