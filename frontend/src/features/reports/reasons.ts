import type { ReportReason, ReportTargetType } from "@/api/types";

export const REPORT_REASONS: Record<ReportTargetType, { code: ReportReason; label: string }[]> = {
  course: [
    { code: "prerequisites_wrong", label: "The prerequisites are wrong" },
    { code: "offered_terms_wrong", label: "It's offered in different terms" },
    { code: "details_wrong", label: "The title, credits, or description is wrong" },
    { code: "other", label: "Something else" },
  ],
  requirement: [
    { code: "missing_course", label: "A course that counts is missing" },
    { code: "course_should_not_count", label: "A course listed here doesn't count" },
    { code: "rule_wrong", label: "The number of courses or credits is wrong" },
    { code: "other", label: "Something else" },
  ],
};
export type ReportTarget = { type: "course"; courseCode: string; title?: string } | { type: "requirement"; requirementId: string; label: string };
