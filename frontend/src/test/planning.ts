import type { Course, Plan, Profile } from "@/api/types";
export const plannedCourse: Course = { code: "TEST 1001", title: "Synthetic course", credits: 3, status: "plan", term: "Spring 2027",
  requirement: "Elective", offered: ["Spring"], prereqs: [], prerequisiteTree: null, concurrent: [], professors: [] };
export const actionPlan: Plan = { terms: ["Completed", "Fall 2026", "Spring 2027", "Fall 2027", "Spring 2028"], currentTerm: "Fall 2026",
  courses: [plannedCourse], baseCredits: 0, catalogTerm: null, availableCatalogTerms: [], warnings: [], requirementProgress: [] };
export const actionProfile: Profile = { name: "", major: "", standing: "", careerGoals: "", creditLoad: 15, graduationTarget: "Spring 2028", onboarded: true };

