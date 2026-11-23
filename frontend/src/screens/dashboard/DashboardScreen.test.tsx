import { http, HttpResponse, delay } from "msw";
import { describe, expect, it } from "vitest";
import { screen, within } from "@testing-library/react";
import { api, server } from "@/test/server";
import { renderWithProviders } from "@/test/render";
import DashboardScreen from "./DashboardScreen";

const profile = { name: "Synthetic", major: "Mini Synthetic B.S.", standing: "Sophomore", careerGoals: "", creditLoad: 15, graduationTarget: "", onboarded: true };
const evidence = { matchedCodes: [], missingCodes: [], appliedAdjustments: [] };
const group = (id: string, label: string, completedStatus: string, projectedStatus: string, missing: string[] = []) => ({
  id, label, parentId: null, type: "group", category: "Major core", completedStatus, projectedStatus,
  completedEvidence: evidence, projectedEvidence: { ...evidence, missingCodes: missing }, details: [],
});
const plan = {
  terms: ["Completed", "Fall 2026", "Spring 2027"], currentTerm: "Fall 2026", baseCredits: 0, courses: [],
  catalogTerm: "Fall 2026", availableCatalogTerms: ["Fall 2026"], warnings: ["requirements_need_review"],
  requirementProgress: [
    group("core", "Mini core", "unsatisfied", "satisfied"),
    group("math", "Mini math", "unsatisfied", "unsatisfied", ["MINI 2001"]),
    { ...group("math-course", "MINI 2001", "unsatisfied", "unsatisfied"), parentId: "math", type: "course" },
  ],
};
const summary = { gpa: 3.62, gradedCredits: 48, creditsCompleted: 120, creditsTotal: 120, percentComplete: 100,
  program: "Mini Synthetic B.S.", source: "Based on the courses you entered" };

function stub(summaryResponse: () => Response | Promise<Response> = () => HttpResponse.json(summary)) {
  server.use(
    http.get(api("/profile"), () => HttpResponse.json(profile)),
    http.get(api("/plan"), () => HttpResponse.json(plan)),
    http.get(api("/summary"), summaryResponse),
  );
}

describe("DashboardScreen", () => {
  it("shows skeletons while the summary loads", async () => {
    stub(async () => {
      await delay("infinite");
      return HttpResponse.json(summary);
    });
    renderWithProviders(<DashboardScreen />);
    expect((await screen.findAllByLabelText("Loading")).length).toBeGreaterThan(0);
  });

  it("shows server values", async () => {
    stub();
    renderWithProviders(<DashboardScreen />);
    expect(await screen.findByText("3.62")).toBeInTheDocument();
  });

  it("shows N/A for missing values", async () => {
    stub(() => HttpResponse.json({ ...summary, gpa: null, percentComplete: null }));
    renderWithProviders(<DashboardScreen />);
    expect((await screen.findAllByText("N/A")).length).toBeGreaterThan(1);
  });

  it("makes summary errors visible", async () => {
    stub(() => HttpResponse.json({ error: "Boom" }, { status: 500 }));
    renderWithProviders(<DashboardScreen />);
    expect(await screen.findByText("We couldn't load your progress.")).toBeInTheDocument();
  });

  it("labels credit progress separately from completed and projected requirements", async () => {
    stub();
    renderWithProviders(<DashboardScreen />);
    expect(await screen.findByText("Credit progress")).toBeInTheDocument();
    expect(screen.getByText(/not a check of your degree requirements/i)).toBeInTheDocument();
    const requirements = await screen.findByRole("region", { name: "Degree requirements" });
    const math = within(requirements).getByText("Mini math").closest("li") as HTMLElement;
    expect(within(math).getByText("Completed: not yet met")).toBeInTheDocument();
    expect(within(math).getByText("With your plan: not yet met")).toBeInTheDocument();
    expect(within(math).getByText(/MINI 2001/)).toBeInTheDocument();
    const core = within(requirements).getByText("Mini core").closest("li") as HTMLElement;
    expect(within(core).getByText("With your plan: met")).toBeInTheDocument();
    expect(screen.getByText(/need review/)).toBeInTheDocument();
  });
});
