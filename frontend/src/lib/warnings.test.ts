import { describe, expect, it } from "vitest";
import { WARNING_TEXT, translateWarning } from "./warnings";

describe("translateWarning", () => {
  it("has plain-language text for every v2 and generation warning", () => {
    for (const code of ["program_requirements_unavailable", "program_version_unavailable", "program_version_unconfirmed",
      "requirements_incomplete", "requirements_need_review", "course_metadata_unavailable", "offered_terms_unverified",
      "prerequisites_require_review", "catalog_version_unverified", "catalog_metadata_conflict", "graduation_target_unreachable"]) {
      expect(WARNING_TEXT[code]).toMatch(/\w+ \w+/);
      expect(translateWarning(code)).not.toContain("_");
    }
  });

  it("never shows a raw code for an unknown warning", () => {
    expect(translateWarning("something_new")).toBe("Some planning information needs review.");
  });
});
