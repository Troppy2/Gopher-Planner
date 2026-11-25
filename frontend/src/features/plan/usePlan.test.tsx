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

it("announces saving until the server confirms the plan", async () => {
  stub();
  let finish!: () => void;
  let saving = false;
  const response = new Promise<Plan>(resolve => { finish = () => resolve(saved); });
  server.use(http.put(api("/plan"), async () => { saving = true; return HttpResponse.json(await response); }));
  const Wrapper = wrapper();
  const Probe = () => { const { add, plan } = usePlan(); return <button disabled={!plan} onClick={() => add("MINI 1101", "Spring 2027")}>Edit</button>; };
  render(<Wrapper><Probe /><UnsavedPlanBar /></Wrapper>);
  await waitFor(() => expect(screen.getByRole("button", { name: "Edit" })).toBeEnabled());
  act(() => screen.getByRole("button", { name: "Edit" }).click());
  expect(await screen.findByText("Saving…")).toBeInTheDocument();
  expect(screen.queryByText("Saved")).not.toBeInTheDocument();
  await waitFor(() => expect(saving).toBe(true), { timeout: 3000 });
  await act(async () => { finish(); });
  expect(await screen.findByText("Saved")).toBeInTheDocument();
});

it("uses fresh current credits when an unchanged course was included in a generated draft", async () => {
  stub();
  let credits = 3;
  server.use(http.get(api("/plan"), () => HttpResponse.json({ ...saved, courses: [{ ...course("MINI 1101", "prog", "Fall 2026"), credits }] })),
    http.post(api("/plans/generate"), () => HttpResponse.json({ jobId: "job", status: "succeeded", warnings: [], plan: {
      ...saved, courses: [course("MINI 1101", "prog", "Fall 2026"), course("MINI 1102", "plan", "Spring 2027")],
    } })));
  const { result } = renderHook(() => usePlan(), { wrapper: wrapper() });
  await waitFor(() => expect(result.current.plan).toBeDefined());
  await act(async () => { await result.current.build(); });
  credits = 2;
  await act(async () => { await result.current.refetch(); });
  // The draft re-merges after the refetched plan renders, which can land a tick later on slow runners.
  await waitFor(() => expect(result.current.courses.find(c => c.code === "MINI 1101")?.credits).toBe(2));
});

it("keeps a newly added class visible while saving", async () => {
  stub();
  let finish!: () => void;
  const added = course("NEWS 1001", "plan", "Spring 2027");
  const response = new Promise<Plan>(resolve => { finish = () => resolve({ ...saved, courses: [...saved.courses, added] }); });
  server.use(http.put(api("/plan"), async () => HttpResponse.json(await response)));
  const { result } = renderHook(() => usePlan(), { wrapper: wrapper() });
  await waitFor(() => expect(result.current.plan).toBeDefined());
  act(() => result.current.addCourse(added, "Spring 2027"));
  let saving!: Promise<unknown>;
  act(() => { saving = result.current.save(); });
  await waitFor(() => expect(result.current.saveState.isPending).toBe(true));
  expect(result.current.courses.find(c => c.code === added.code)?.status).toBe("plan");
  await act(async () => { finish(); await saving; });
});

it("moves an in-progress class to a future term and refreshes dashboard data after saving", async () => {
  const calls = stub();
  let summaryReads = 0, courseworkReads = 0;
  server.use(http.get(api("/plan"), () => HttpResponse.json({ ...saved, catalogTerm: "Fall 2026", courses: [course("MINI 1101", "prog", "Fall 2026")] })),
    http.get(api("/summary"), () => { summaryReads++; return HttpResponse.json({ creditsCompleted: 0, creditsTotal: 24 }); }),
    http.get(api("/coursework"), () => { courseworkReads++; return HttpResponse.json({ courses: [], skipped: false }); }));
  const { result } = renderHook(() => usePlan(), { wrapper: wrapper() });
  await waitFor(() => expect(result.current.summary).toBeDefined());
  act(() => result.current.add("MINI 1101", "Spring 2027"));
  expect(result.current.courses[0].status).toBe("plan");
  act(() => result.current.add("MINI 1101", "Fall 2026"));
  expect(result.current.courses[0].status).toBe("prog");
  act(() => result.current.add("MINI 1101", "Spring 2027"));
  await act(async () => { await result.current.save(); });
  expect(calls.put[0]).toMatchObject({ changes: [{ code: "MINI 1101", status: "plan" }] });
  await waitFor(() => expect(summaryReads).toBeGreaterThan(1));
  expect(courseworkReads).toBe(0);
});

it("keeps generated slot labels in the draft and sends them when saving", async () => {
  const calls = stub();
  server.use(http.post(api("/plans/generate"), () => HttpResponse.json({ jobId: "slot-job", status: "succeeded", warnings: [], plan: {
    ...saved, electiveCredits: 21, catalogTerm: "Fall 2026", courses: [{ ...course("MINI 1101", "plan", "Spring 2027"), slot: "Synthetic arts" }],
  } })));
  const { result } = renderHook(() => usePlan(), { wrapper: wrapper() });
  await waitFor(() => expect(result.current.plan).toBeDefined());
  await act(async () => { await result.current.build(); });
  expect(result.current.courses.find(c => c.code === "MINI 1101")?.slot).toBe("Synthetic arts");
  expect(result.current.plan?.electiveCredits).toBe(21);
  await act(async () => { await result.current.save(); });
  expect(calls.put[0]).toMatchObject({ changes: [{ code: "MINI 1101", slot: "Synthetic arts" }] });
});

it("removes saved placements omitted by generation and saves removal without a slot", async () => {
  const calls = stub();
  server.use(http.get(api("/plan"), () => HttpResponse.json({ ...saved, courses: [
    { ...course("MINI 1101", "plan", "Spring 2027"), slot: "Synthetic arts" },
  ] })), http.post(api("/plans/generate"), () => HttpResponse.json({ jobId: "job", status: "succeeded", warnings: [], plan: { ...saved, courses: [] } })));
  const { result } = renderHook(() => usePlan(), { wrapper: wrapper() });
  await waitFor(() => expect(result.current.plan).toBeDefined());
  await act(async () => { await result.current.build(); });
  expect(result.current.courses.find(c => c.code === "MINI 1101")?.status).toBe("avail");
  await act(async () => { await result.current.save(); });
  expect(calls.put[0]).toMatchObject({ changes: [{ code: "MINI 1101", status: "avail", term: null }] });
  expect(JSON.stringify(calls.put[0])).not.toContain('"slot"');
});

it("does not label an unknown program's remaining credits as free electives", async () => {
  stub();
  server.use(http.get(api("/plan"), () => HttpResponse.json({ ...saved, electiveCredits: 0 })));
  const { result } = renderHook(() => usePlan(), { wrapper: wrapper() });
  await waitFor(() => expect(result.current.summary).toBeDefined());
  expect(result.current.plan?.electiveCredits).toBe(0);
});

it("restores the generated elective baseline after a failed save", async () => {
  stub({ putStatus: 409 });
  server.use(http.post(api("/plans/generate"), () => HttpResponse.json({ jobId: "job", status: "succeeded", warnings: [], plan: {
    ...saved, electiveCredits: 7, catalogTerm: "Fall 2026", courses: [course("MINI 1101", "plan", "Spring 2027")],
  } })));
  const { result } = renderHook(() => usePlan(), { wrapper: wrapper() });
  await waitFor(() => expect(result.current.plan).toBeDefined());
  await act(async () => { await result.current.build(); });
  expect(result.current.plan?.electiveCredits).toBe(7);
  await act(async () => { await result.current.save(); });
  expect(result.current.plan?.electiveCredits).toBe(7);
});

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
    expect(await screen.findByText("MINI 1102 needs MINI 1101 in an earlier term.", {}, { timeout: 3000 })).toBeInTheDocument();
    expect(usePlanDraft.getState().changes["MINI 1102"]).toEqual({ status: "plan", term: "Spring 2027" });
    act(() => usePlanDraft.getState().clear());
  });
});
