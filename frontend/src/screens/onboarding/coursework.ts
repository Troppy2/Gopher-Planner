import type { CourseworkEntry, TermId } from "@/api/types";
import type { ManualCourse } from "./onboarding.store";

/**
 * Manual onboarding entries in the coursework contract. In-progress rows take the current term;
 * completed rows keep a term and grade carried over from a transcript, otherwise both are unknown.
 */
export function toCourseworkEntries(manual: ManualCourse[], current: TermId): CourseworkEntry[] {
  return manual.map((course) => ({
    code: course.code,
    title: course.title,
    credits: course.credits,
    status: course.status,
    term: course.status === "prog" ? current : course.term ?? null,
    grade: course.status === "done" ? course.grade ?? null : null,
  }));
}

/** A saved or parsed coursework row as an editable manual entry, keeping its term and grade. */
export function toManualCourse(course: CourseworkEntry): ManualCourse {
  return { code: course.code, title: course.title, credits: course.credits, status: course.status, term: course.term, grade: course.grade };
}
