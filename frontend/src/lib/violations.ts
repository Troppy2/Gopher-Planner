import type { Violation } from "@/api/client";

/** Plain-language text for each plan save violation the server returns. */
export function violationText({ code, reason, detail }: Violation) {
  switch (reason) {
    case "prerequisite_not_before":
      return `${code} needs ${detail} in an earlier term.`;
    case "not_offered_in_season":
      return `${code} isn't offered in ${detail} terms.`;
    case "locked_course":
      return `${code} is already ${detail === "prog" ? "in progress" : "completed"} and can't be moved.`;
    case "course_metadata_unavailable":
      return detail === "catalog_metadata_conflict"
        ? `Official sources disagree about ${code}. Ask your advisor before planning it.`
        : `${code} is missing prerequisite information and can't be scheduled yet.`;
    default:
      return `${code} can't be placed there.`;
  }
}
