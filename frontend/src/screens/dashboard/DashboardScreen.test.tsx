import { http, HttpResponse } from "msw";
import { expect, it } from "vitest";
import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { api, server } from "@/test/server";
import { renderWithProviders } from "@/test/render";
import { actionPlan, actionProfile, plannedCourse } from "@/test/planning";
import { CourseworkEditor } from "@/features/coursework/CourseworkEditor";
import DashboardScreen from "./DashboardScreen";

it("refreshes dashboard credits and plan after coursework credit corrections", async () => {
  let earned = 4, planReads = 0, summaryReads = 0;
  const coursework = () => ({ skipped: false, courses: [{ code: "TEST 1001", title: "Synthetic completed class", credits: earned,
    status: "done", grade: "A", term: "Spring 2026" }] });
  server.use(
    http.get(api("/coursework"), () => HttpResponse.json(coursework())),
    http.put(api("/coursework"), async ({ request }) => {
      const body = await request.json() as ReturnType<typeof coursework>;
      earned = body.courses[0].credits;
      return HttpResponse.json(coursework());
    }),
    http.get(api("/plan"), () => { planReads++; return HttpResponse.json({ ...actionPlan, courses: [{ ...plannedCourse, credits: earned, status: "done" }] }); }),
    http.get(api("/profile"), () => HttpResponse.json(actionProfile)),
    http.get(api("/summary"), () => { summaryReads++; return HttpResponse.json({ creditsCompleted: earned, creditsTotal: 24,
      gpa: 4, gradedCredits: earned, percentComplete: Math.round(earned / 24 * 100), program: "Synthetic", source: "Synthetic coursework" }); }),
  );
  renderWithProviders(<><DashboardScreen /><CourseworkEditor /></>);
  const metric = (await screen.findByRole("heading", { name: "Completed credits" })).closest("section")!;
  expect(within(metric).getByText("20 credits remaining")).toBeInTheDocument();
  const input = await screen.findByRole("textbox", { name: "TEST 1001 credits" });
  await userEvent.clear(input);
  await userEvent.type(input, "2");
  await userEvent.tab();
  await waitFor(() => expect(within(metric).getByText("22 credits remaining")).toBeInTheDocument(), { timeout: 3000 });
  expect(summaryReads).toBeGreaterThan(1);
  await waitFor(() => expect(planReads).toBeGreaterThan(1));
});
