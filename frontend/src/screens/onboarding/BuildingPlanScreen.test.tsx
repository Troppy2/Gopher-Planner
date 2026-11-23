import { http, HttpResponse } from "msw";
import { describe, expect, it } from "vitest";
import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { api, server } from "@/test/server";
import { renderWithProviders } from "@/test/render";
import BuildingPlanScreen from "./BuildingPlanScreen";

const basePlan = {
  terms: ["Completed", "Fall 2026", "Spring 2027"], currentTerm: "Fall 2026", baseCredits: 0, courses: [],
  catalogTerm: null as string | null, availableCatalogTerms: ["Fall 2026"], warnings: ["program_version_unconfirmed"], requirementProgress: [],
};

interface Result { warnings?: string[]; status?: number }

function stub({ plan = basePlan, results = [{ warnings: [] }] as Result[] } = {}) {
  const calls: { generate: unknown[]; profile: unknown[] } = { generate: [], profile: [] };
  server.use(
    http.get(api("/plan"), () => HttpResponse.json(plan)),
    http.post(api("/plans/generate"), async ({ request }) => {
      calls.generate.push(await request.json());
      const result = results[Math.min(calls.generate.length - 1, results.length - 1)];
      if (result.status) return HttpResponse.json({ error: "Plan generation failed", code: "generation_failed" }, { status: result.status });
      return HttpResponse.json({ jobId: "job", status: "succeeded", warnings: result.warnings ?? [], plan: { ...plan, warnings: result.warnings ?? [] } });
    }),
    http.put(api("/profile"), async ({ request }) => {
      calls.profile.push(await request.json());
      return HttpResponse.json({ name: "", major: "", standing: "", careerGoals: "", creditLoad: 15, graduationTarget: "", onboarded: true });
    }),
  );
  return calls;
}

describe("BuildingPlanScreen", () => {
  it("requires an explicit catalog term before generating a known program", async () => {
    const calls = stub();
    renderWithProviders(<BuildingPlanScreen />);
    expect(await screen.findByRole("radio", { name: "Fall 2026" })).toBeInTheDocument();
    expect(calls.generate).toHaveLength(0);
    await userEvent.click(screen.getByRole("radio", { name: "Fall 2026" }));
    await userEvent.click(screen.getByRole("button", { name: "Build my plan" }));
    expect(await screen.findByText("Navigated away")).toBeInTheDocument();
    expect(calls.generate).toEqual([{ dryRun: false, catalogTerm: "Fall 2026" }]);
    expect(calls.profile).toEqual([{ onboarded: true }]);
  });

  it("does not complete onboarding when the version is still unconfirmed", async () => {
    const calls = stub({ plan: { ...basePlan, catalogTerm: "Fall 2026" }, results: [{ warnings: ["program_version_unconfirmed"] }] });
    renderWithProviders(<BuildingPlanScreen />);
    expect(await screen.findByText(/Choose the catalog year/)).toBeInTheDocument();
    expect(calls.profile).toEqual([]);
  });

  it("shows a failure and really retries", async () => {
    const calls = stub({ plan: { ...basePlan, catalogTerm: "Fall 2026", warnings: [] }, results: [{ status: 500 }, { warnings: [] }] });
    renderWithProviders(<BuildingPlanScreen />);
    expect(await screen.findByText("We couldn't build your plan.")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Try again" }));
    expect(await screen.findByText("Navigated away")).toBeInTheDocument();
    expect(calls.generate).toHaveLength(2);
    expect(calls.profile).toEqual([{ onboarded: true }]);
  });

  it("explains an unknown program in words and still finishes onboarding", async () => {
    const calls = stub({ plan: { ...basePlan, availableCatalogTerms: [], warnings: ["program_requirements_unavailable"] },
      results: [{ warnings: ["program_requirements_unavailable"] }] });
    renderWithProviders(<BuildingPlanScreen />);
    expect(await screen.findByText("Your plan is ready")).toBeInTheDocument();
    expect(screen.getByText(/don't have requirements for your major yet/)).toBeInTheDocument();
    expect(calls.generate).toEqual([{ dryRun: false }]);
    expect(calls.profile).toEqual([{ onboarded: true }]);
  });
});
