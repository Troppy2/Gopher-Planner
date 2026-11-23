/** Plain-language text for every planning warning code the API can return. */
export const WARNING_TEXT: Record<string, string> = {
  program_requirements_unavailable: "We don't have requirements for your major yet, so no program courses were planned. Add courses from the catalog.",
  program_version_unavailable: "That catalog year isn't available for your major. Choose one of the supported years.",
  program_version_unconfirmed: "Choose the catalog year you follow before we apply your major's requirements.",
  requirements_incomplete: "Some degree requirements are not covered by this plan yet.",
  requirements_need_review: "Some requirements need review by you or your advisor before they count.",
  course_metadata_unavailable: "Some courses are missing prerequisite information, so they can't be scheduled automatically.",
  offered_terms_unverified: "Some courses don't list which semesters they are offered. Check the class schedule before registering.",
  prerequisites_require_review: "Some prerequisites are written as text the planner can't check. Confirm them before registering.",
  catalog_version_unverified: "Some course details come from an older catalog and may have changed.",
  catalog_metadata_conflict: "Official sources disagree about some courses. Ask your advisor before planning them.",
  graduation_target_unreachable: "This plan doesn't reach your degree credit total yet. Add liberal education and elective courses to close the gap.",
};

export function translateWarning(code: string) {
  return WARNING_TEXT[code] ?? "Some planning information needs review.";
}
