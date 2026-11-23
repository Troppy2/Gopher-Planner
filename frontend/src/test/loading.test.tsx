import { http, HttpResponse } from "msw";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { act, screen, waitFor } from "@testing-library/react";
import { api, server } from "./server";
import { renderWithProviders } from "./render";
import { actionPlan, actionProfile } from "./planning";
import { usePlanDraft } from "@/features/plan/plan.store";
import DashboardScreen from "@/screens/dashboard/DashboardScreen";
import FlowChartScreen from "@/screens/flow-chart/FlowChartScreen";
import SettingsScreen from "@/screens/settings/SettingsScreen";
import CatalogScreen from "@/screens/course-catalog/CatalogScreen";
import { CourseDrawer } from "@/features/course-detail/CourseDrawer";
import { CourseworkEditor } from "@/features/coursework/CourseworkEditor";
import ProfileScreen from "@/screens/onboarding/ProfileScreen";
import { useOnboarding } from "@/screens/onboarding/onboarding.store";

beforeEach(() => {
  usePlanDraft.getState().clear(); useOnboarding.getState().reset();
  vi.stubGlobal("ResizeObserver", class { observe() {} disconnect() {} });
  vi.spyOn(HTMLCanvasElement.prototype, "getContext").mockReturnValue(null);
});
afterEach(() => vi.unstubAllGlobals());

const course = { id: 1, code: "TEST 1001", subject: "TEST", number: "1001", title: "Synthetic course", campus: "Synthetic",
  description: "Synthetic course description.", minimumCredits: 3, maximumCredits: 3, typicallyOffered: "Spring", offered: ["Spring"],
  prerequisites: { status: "none", requirements: null }, prerequisiteStatus: "none", prerequisiteSourceText: "", unresolvedPrerequisiteCourses: [] };

it.each([
  { name: "dashboard", ui: <DashboardScreen />, ready: "Current classes" },
  { name: "plan", ui: <FlowChartScreen />, ready: "Spring 2027" },
  { name: "plan", ui: <FlowChartScreen />, ready: "Reset view", route: "/?view=graph" },
  { name: "settings", ui: <SettingsScreen />, ready: "Academic goals" },
  { name: "catalog courses", ui: <CatalogScreen />, ready: "Synthetic course" },
  { name: "course details", ui: <CourseDrawer />, ready: "Synthetic course description." },
  { name: "coursework", ui: <CourseworkEditor />, ready: "Synthetic completed course" },
  { name: "profile", ui: <ProfileScreen />, ready: "Name" },
])("replaces the $name skeleton with loaded content", async ({ name, ui, ready, route }) => {
  let finish!: () => void;
  const pending = new Promise<void>(resolve => { finish = resolve; });
  server.use(http.get(api("/*"), async ({ request }) => {
    await pending;
    const path = new URL(request.url).pathname;
    const data = path.endsWith("/profile") ? actionProfile : path.endsWith("/plan") ? actionPlan
      : path.endsWith("/summary") ? { creditsCompleted: 0, creditsTotal: 24, gpa: null, percentComplete: null }
      : path.endsWith("/programs") ? { programs: [] }
      : path.endsWith("/coursework") ? { courses: [{ code: "TEST 1001", title: "Synthetic completed course", credits: 3, status: "done", term: "Spring 2026", grade: "A" }], skipped: false }
      : path.endsWith("/courses") ? { courses: [course], total: 1, limit: 20, offset: 0 } : course;
    return HttpResponse.json(data);
  }));
  renderWithProviders(ui, { route: route ?? "/?course=TEST+1001" });
  try {
    const loading = await screen.findByRole("status", { name: `Loading ${name}` });
    expect(loading.querySelector('[aria-busy="true"]')).toBeInTheDocument();
    expect(loading.querySelectorAll('[aria-hidden="true"]').length).toBeGreaterThan(0);
    expect(screen.queryByText("No courses saved yet. Search below or upload your APAS PDF.")).not.toBeInTheDocument();
  } finally {
    await act(async () => { finish(); });
  }
  await waitFor(() => expect(screen.queryByRole("status", { name: `Loading ${name}` })).not.toBeInTheDocument());
  expect((await screen.findAllByText(ready)).length).toBeGreaterThan(0);
});
