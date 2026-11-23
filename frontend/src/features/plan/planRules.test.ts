import { describe, expect, it } from "vitest";
import type { CatalogCourse, Course, Plan } from "@/api/types";
import { catalogToPlanCourse, eligible } from "./planRules";

const catalog = (overrides: Partial<CatalogCourse> = {}): CatalogCourse => ({
  id: 1, code: "CSCI 4041", subject: "CSCI", number: "4041", title: "Algorithms", campus: "Twin Cities", description: "",
  minimumCredits: 4, maximumCredits: 4, repeatable: "No", maximumCompletions: "1", maximumCreditsEarned: "4", gradingBasis: "",
  requirements: null, typicallyOffered: "Every Fall & Spring", offered: ["Fall", "Spring"], prerequisiteStatus: "found",
  prerequisiteSourceText: "", unresolvedPrerequisiteCourses: [],
  prerequisites: { status: "found", needs_review: false, source_text: "", requirements: { type: "any_of", requirements: [
    { type: "course", course_code: "CSCI 1913" }, { type: "course", course_code: "CSCI 1933" }] } },
  ...overrides,
});

const course = (code: string, status: Course["status"], term: string | null, extra: Partial<Course> = {}): Course => ({
  code, title: code, credits: 4, status, requirement: "Major core", offered: ["Fall", "Spring"], prereqs: [], concurrent: [],
  professors: [], term, ...extra,
});

describe("catalogToPlanCourse", () => {
  it("maps a catalog course to an available elective with display prerequisites and the full tree", () => {
    expect(catalogToPlanCourse(catalog())).toMatchObject({
      code: "CSCI 4041", title: "Algorithms", credits: 4, status: "avail", requirement: "Elective", offered: ["Fall", "Spring"],
      prereqs: ["CSCI 1913", "CSCI 1933"], concurrent: [], professors: [], term: null, metadataSource: "catalog",
      prerequisiteTree: { type: "any_of" },
    });
  });

  it("blocks a course whose prerequisite information is unknown, with a readable reason", () => {
    const blocked = catalogToPlanCourse(catalog({ prerequisites: null }));
    expect(blocked.status).toBe("block");
    expect(blocked.lockReason).toMatch(/Prerequisite information/);
  });

  it("treats a verified empty prerequisite record as no prerequisites", () => {
    const free = catalogToPlanCourse(catalog({ prerequisites: { status: "none", needs_review: false, source_text: "", requirements: null } }));
    expect([free.status, free.prereqs, free.prerequisiteTree]).toEqual(["avail", [], null]);
  });
});

describe("eligible", () => {
  const plan: Pick<Plan, "terms"> = { terms: ["Completed", "Fall 2026", "Spring 2027", "Fall 2027"] };

  it("evaluates any_of trees instead of requiring every flat prerequisite", () => {
    const target = catalogToPlanCourse(catalog());
    const done = course("CSCI 1933", "done", "Completed");
    const missing = course("CSCI 1913", "avail", null);
    expect(eligible(target, 2, [target, done, missing], plan.terms)).toBe(true);
    expect(eligible(target, 2, [target, missing], plan.terms)).toBe(false);
  });

  it("requires planned prerequisites in a strictly earlier term", () => {
    const target = catalogToPlanCourse(catalog());
    const planned = course("CSCI 1913", "plan", "Spring 2027");
    expect(eligible(target, 2, [target, planned], plan.terms)).toBe(false);
    expect(eligible(target, 3, [target, planned], plan.terms)).toBe(true);
  });
});
