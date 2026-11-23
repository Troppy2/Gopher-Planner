import { http, HttpResponse } from "msw";
import { beforeEach, describe, expect, it } from "vitest";
import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { api, server } from "@/test/server";
import { renderWithProviders } from "@/test/render";
import type { CatalogCourse } from "@/api/types";
import { usePlanDraft } from "@/features/plan/plan.store";
import { CourseDrawer } from "@/features/course-detail/CourseDrawer";
import CatalogScreen from "./CatalogScreen";

const catalogCourse = (code: string, prerequisites: CatalogCourse["prerequisites"]): CatalogCourse => ({
  id: 1, code, subject: code.split(" ")[0], number: code.split(" ")[1], title: `Synthetic ${code}`, campus: "Twin Cities", description: "",
  minimumCredits: 3, maximumCredits: 3, repeatable: "No", maximumCompletions: "1", maximumCreditsEarned: "3", gradingBasis: "",
  requirements: null, typicallyOffered: "Every Fall & Spring", offered: ["Fall", "Spring"], prerequisiteStatus: prerequisites?.status ?? "",
  prerequisiteSourceText: "", prerequisites, unresolvedPrerequisiteCourses: [],
});
const free = catalogCourse("CSCI 1001", { status: "none", needs_review: false, source_text: "", requirements: null });
const unknown = catalogCourse("CSCI 1002", null);
const plan = { terms: ["Completed", "Fall 2026", "Spring 2027", "Fall 2027"], currentTerm: "Fall 2026", baseCredits: 0, courses: [],
  catalogTerm: null, availableCatalogTerms: [], warnings: ["program_requirements_unavailable"], requirementProgress: [] };

beforeEach(() => {
  usePlanDraft.getState().clear();
  server.use(
    http.get(api("/plan"), () => HttpResponse.json(plan)),
    http.get(api("/profile"), () => HttpResponse.json({ name: "", major: "Undeclared", standing: "", careerGoals: "", creditLoad: 15, graduationTarget: "", onboarded: true })),
    http.get(api("/summary"), () => HttpResponse.json({ gpa: null, gradedCredits: 0, creditsCompleted: 0, creditsTotal: 120, percentComplete: null, program: "", source: "" })),
    http.get(api("/courses"), () => HttpResponse.json({ courses: [free], total: 1, limit: 25, offset: 0 })),
    http.get(api("/courses/:code"), ({ params }) => HttpResponse.json(params.code === "CSCI 1002" ? unknown : free)),
  );
});

describe("adding catalog-only courses", () => {
  it("adds a catalog result that is not in the saved plan", async () => {
    renderWithProviders(<CatalogScreen />, { path: "/catalog", route: "/catalog" });
    await userEvent.click(await screen.findByRole("button", { name: "Add CSCI 1001 to plan" }));
    expect(usePlanDraft.getState().changes["CSCI 1001"]).toEqual({ status: "plan", term: "Spring 2027" });
    expect(usePlanDraft.getState().extras["CSCI 1001"]).toMatchObject({ requirement: "Elective", metadataSource: "catalog" });
  });

  it("adds a catalog-only course from the course drawer", async () => {
    renderWithProviders(<CourseDrawer />, { path: "/catalog", route: "/catalog?course=CSCI%201001" });
    await userEvent.click(await screen.findByRole("button", { name: "Add to Spring 2027" }));
    expect(usePlanDraft.getState().changes["CSCI 1001"]).toEqual({ status: "plan", term: "Spring 2027" });
  });

  it("disables Add with a readable reason when prerequisite information is unknown", async () => {
    renderWithProviders(<CourseDrawer />, { path: "/catalog", route: "/catalog?course=CSCI%201002" });
    expect(await screen.findByText(/Prerequisite information for this course isn't available/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Add to plan" })).toBeDisabled();
  });
});
