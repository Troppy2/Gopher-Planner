import { http, HttpResponse } from "msw";
import { expect, it, vi } from "vitest";
import { act, screen, waitFor } from "@testing-library/react";
import { api, server } from "@/test/server";
import { renderWithProviders } from "@/test/render";
import { actionPlan, actionProfile } from "@/test/planning";
import { usePlanDraft } from "@/features/plan/plan.store";
import FlowChartScreen from "./FlowChartScreen";

it("keeps the user's scroll position when generation finishes", async () => {
  usePlanDraft.getState().clear();
  const scroll = vi.fn();
  const previous = HTMLElement.prototype.scrollIntoView;
  HTMLElement.prototype.scrollIntoView = scroll;
  vi.stubGlobal("requestAnimationFrame", (callback: FrameRequestCallback) => { callback(0); return 1; });
  let finish!: () => void, calls = 0;
  const ready = new Promise<void>(resolve => { finish = resolve; });
  const plan = { ...actionPlan, catalogTerm: "Fall 2026" };
  server.use(http.get(api("/plan"), () => HttpResponse.json(plan)),
    http.get(api("/profile"), () => HttpResponse.json(actionProfile)),
    http.get(api("/summary"), () => HttpResponse.json({ creditsCompleted: 0, creditsTotal: 24 })),
    http.post(api("/plans/generate"), async () => { calls++; await ready; return HttpResponse.json({ jobId: "synthetic", status: "succeeded", warnings: [], plan }); }));
  try {
    renderWithProviders(<FlowChartScreen />, { route: "/?build=1" });
    await screen.findByText("Building your plan…");
    await act(async () => { finish(); });
    await waitFor(() => expect(screen.queryByText("Building your plan…")).not.toBeInTheDocument());
    expect(calls).toBe(1);
    expect(scroll).not.toHaveBeenCalled();
  } finally {
    HTMLElement.prototype.scrollIntoView = previous;
    vi.unstubAllGlobals();
    usePlanDraft.getState().clear();
  }
});
