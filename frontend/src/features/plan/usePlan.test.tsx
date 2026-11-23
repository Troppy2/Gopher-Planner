import type { ReactNode } from "react";
import { http, HttpResponse } from "msw";
import { beforeEach, describe, expect, it } from "vitest";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { act, render, renderHook, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router";
import { api, server } from "@/test/server";
import type { Course, Plan } from "@/api/types";
import { usePlan } from "./usePlan";
import { usePlanDraft } from "./plan.store";
import { UnsavedPlanBar } from "./UnsavedPlanBar";

const course = (code: string, status: Course["status"], term: string | null): Course => ({
  code, title: code, credits: 3, status, requirement: "Major core", offered: ["Fall", "Spring"], prereqs: [], concurrent: [],
  professors: [], term, prerequisiteTree: null, metadataSource: "program", metadataWarnings: [],
});
const saved: Plan = {
  terms: ["Completed", "Fall 2026", "Spring 2027", "Fall 2027"], currentTerm: "Fall 2026", baseCredits: 0,
  courses: [course("MINI 1101", "avail", null), course("MINI 1102", "avail", null)],
  catalogTerm: null, availableCatalogTerms: ["Fall 2026"], warnings: ["program_version_unconfirmed"], requirementProgress: [],
};
const profile = { name: "", major: "Mini Synthetic B.S.", standing: "", careerGoals: "", creditLoad: 15, graduationTarget: "", onboarded: true };

function stub({ putStatus = 200 } = {}) {
  const calls: { generate: unknown[]; put: unknown[] } = { generate: [], put: [] };
  server.use(
    http.get(api("/plan"), () => HttpResponse.json(saved)),
    http.get(api("/profile"), () => HttpResponse.json(profile)),
    http.get(api("/summary"), () => HttpResponse.json({ gpa: null, gradedCredits: 0, creditsCompleted: 0, creditsTotal: 24, percentComplete: null, program: "", source: "" })),
    http.post(api("/plans/generate"), async ({ request }) => {
      calls.generate.push(await request.json());
      const draft = { ...saved, catalogTerm: "Fall 2026", warnings: [], courses: [course("MINI 1101", "plan", "Spring 2027"), course("MINI 1102", "plan", "Fall 2027")] };
      return HttpResponse.json({ jobId: "job", status: "succeeded", warnings: [], plan: draft });
    }),
    http.put(api("/plan"), async ({ request }) => {
      calls.put.push(await request.json());
      if (putStatus === 409) {
        return HttpResponse.json({ error: "The resulting plan breaks a scheduling rule", code: "plan_invalid",
          violations: [{ code: "MINI 1102", reason: "prerequisite_not_before", detail: "MINI 1101" }] }, { status: 409 });
      }
      return HttpResponse.json(saved);
    }),
  );
  return calls;
}

function wrapper() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } });
  return ({ children }: { children: ReactNode }) => (
    <QueryClientProvider client={client}><MemoryRouter>{children}</MemoryRouter></QueryClientProvider>
  );
}

beforeEach(() => usePlanDraft.getState().clear());

describe("usePlan", () => {
  it("build runs a dry-run generation with the selected catalog term and keeps it as an unsaved draft", async () => {
    const calls = stub();
    const { result } = renderHook(() => usePlan(), { wrapper: wrapper() });
    await waitFor(() => expect(result.current.plan).toBeDefined());
    act(() => result.current.selectCatalogTerm("Fall 2026"));
    await act(async () => { await result.current.build(); });
    expect(calls.generate).toEqual([{ dryRun: true, catalogTerm: "Fall 2026" }]);
    expect(calls.put).toEqual([]);
    expect(result.current.pendingCount).toBe(2);
    expect(result.current.courses.find((c) => c.code === "MINI 1102")).toMatchObject({ status: "plan", term: "Fall 2027" });
    await act(async () => { await result.current.save(); });
    expect(calls.put).toEqual([{ changes: [
      { code: "MINI 1101", status: "plan", term: "Spring 2027" }, { code: "MINI 1102", status: "plan", term: "Fall 2027" }], catalogTerm: "Fall 2026" }]);
  });

  it("adds a catalog-only course that is not in the saved plan and saves it", async () => {
    const calls = stub();
    const { result } = renderHook(() => usePlan(), { wrapper: wrapper() });
    await waitFor(() => expect(result.current.plan).toBeDefined());
    act(() => result.current.selectCatalogTerm("Fall 2026"));
    act(() => result.current.addCourse({ ...course("CSCI 1001", "avail", null), requirement: "Elective", metadataSource: "catalog" }, "Spring 2027"));
    expect(result.current.courses.find((c) => c.code === "CSCI 1001")).toMatchObject({ status: "plan", term: "Spring 2027", requirement: "Elective" });
    await act(async () => { await result.current.save(); });
    expect(calls.put).toEqual([{ changes: [{ code: "CSCI 1001", status: "plan", term: "Spring 2027" }], catalogTerm: "Fall 2026" }]);
  });

  it("restores the draft and explains a 409 violation in words", async () => {
    stub({ putStatus: 409 });
    const client = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } });
    const Probe = () => {
      const { add } = usePlan();
      return <button onClick={() => add("MINI 1102", "Spring 2027")}>Add</button>;
    };
    render(<QueryClientProvider client={client}><MemoryRouter><Probe /><UnsavedPlanBar /></MemoryRouter></QueryClientProvider>);
    act(() => usePlanDraft.getState().selectCatalogTerm("Fall 2026"));
    await waitFor(() => expect(client.getQueryData(["plan"])).toBeDefined());
    act(() => screen.getByRole("button", { name: "Add" }).click());
    act(() => screen.getByRole("button", { name: "Save plan" }).click());
    expect(await screen.findByText("MINI 1102 needs MINI 1101 in an earlier term.")).toBeInTheDocument();
    expect(usePlanDraft.getState().changes["MINI 1102"]).toEqual({ status: "plan", term: "Spring 2027" });
  });
});
