import { http, HttpResponse } from "msw";
import { expect, it, vi } from "vitest";
import { screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { api, server } from "@/test/server";
import { renderWithProviders } from "@/test/render";
import { actionPlan, actionProfile, plannedCourse } from "@/test/planning";
import type { CatalogCourse, LeCategory, LeItemStatus, LiberalEd, Plan } from "@/api/types";
import { LiberalEdPanel } from "./LiberalEdPanel";

const none = { done: [], prog: [], plan: [] };

const category = (id: string, label: string, status: LeItemStatus = "needed", extra: Partial<LeCategory> = {}): LeCategory => ({
  id, label, designations: [label], status, source: "catalog", codes: none, ...extra,
});

const liberal = (overrides: Partial<LiberalEd> = {}): LiberalEd => ({
  source: "catalog",
  core: {
    status: "short",
    items: [
      category("literature", "Literature", "done", { codes: { done: ["SYN 1001"], prog: [], plan: [] } }),
      category("historical-perspectives", "Historical Perspectives", "planned", { codes: { done: [], prog: [], plan: ["TEST 1001"] } }),
      category("arts-humanities", "Arts/Humanities"),
    ],
  },
  themes: {
    status: "short", required: 4, completed: 1, projected: 1, mandatory: ["race-power-justice"], mandatoryMissing: ["race-power-justice"],
    items: [
      category("global-perspectives", "Global Perspectives", "done", { source: "apas" }),
      category("race-power-justice", "Race, Power, and Justice in the US", "needed", { designations: ["Race, Power, and Justice US", "Diversity and Soc Justice US"] }),
    ],
  },
  writing: {
    firstYear: { label: "First-year writing", status: "needed", codes: none, acceptedCodes: ["WRIT 1301", "WRIT 1401"] },
    intensive: {
      label: "Writing intensive", status: "short",
      required: { total: 4, upper: 2, upperInMajor: 1 },
      completed: { total: 1, upper: 0, upperInMajor: 0 },
      projected: { total: 2, upper: 1, upperInMajor: 1 },
      codes: { done: ["SYN 1001W"], prog: [], plan: ["CSCI 3001W"] },
    },
  },
  remaining: ["Arts/Humanities", "Race, Power, and Justice US", "Writing Intensive"],
  sources: {},
  ...overrides,
});

const catalogCourse = (code: string): CatalogCourse => ({
  id: 1, code, subject: code.split(" ")[0], number: code.split(" ")[1], title: `Synthetic ${code}`, campus: "Twin Cities",
  description: "", minimumCredits: 3, maximumCredits: 3, repeatable: "No", maximumCompletions: "1", maximumCreditsEarned: "3",
  gradingBasis: "", requirements: null, typicallyOffered: "Fall, Spring", offered: ["Fall", "Spring"], prerequisiteStatus: "none",
  leAttributes: [], prerequisiteSourceText: "",
  prerequisites: { needs_review: false, source_text: "", status: "none", requirements: null }, unresolvedPrerequisiteCourses: [],
});

const plan = (le: LiberalEd = liberal()): Plan => ({ ...actionPlan, liberalEd: le });

function render(le?: LiberalEd, onAdd = vi.fn()) {
  renderWithProviders(<LiberalEdPanel plan={plan(le)} profile={actionProfile} courses={[plannedCourse]} onAdd={onAdd} />);
  return onAdd;
}

it("shows each section's status, evidence and links for needed categories", async () => {
  server.use(http.get(api("/liberal-ed/double-dippers"), () => HttpResponse.json({ remaining: [], courses: [], total: 0, limit: 5, offset: 0 })));
  render();
  const core = screen.getByRole("heading", { name: "Diversified core" }).closest(".le-section") as HTMLElement;
  expect(within(core).getByText("Short")).toBeVisible();
  expect(within(core).getByText("SYN 1001")).toBeVisible();
  expect(within(core).getByText("TEST 1001 (Spring 2027)")).toBeVisible();
  expect(within(core).getByRole("link", { name: "Find Arts/Humanities courses" })).toHaveAttribute("href", "/catalog?le=Arts%2FHumanities");
  expect(screen.getByText("1 of 4 done, 1 with your plan. Race, Power, and Justice in the US is required.")).toBeVisible();
  expect(screen.getByText("Complete on your APAS audit")).toBeVisible();
  expect(screen.getByText(/WRIT 1301 or WRIT 1401, or an approved equivalent/)).toBeVisible();
  expect(screen.getByText(/1 of 4 done, 0 of 2 upper division, 0 of 1 upper division in your major\. 2 with your plan\./)).toBeVisible();
  expect(screen.getByRole("link", { name: "Find writing intensive courses" })).toHaveAttribute("href", "/catalog?le=Writing%20Intensive");
});

it("lists courses that count twice and adds one to the earliest fitting term", async () => {
  server.use(http.get(api("/liberal-ed/double-dippers"), () => HttpResponse.json({
    remaining: [], total: 1, limit: 5, offset: 0,
    courses: [{ ...catalogCourse("SYN 2001W"), covers: ["Arts/Humanities", "Writing Intensive"] }],
  })));
  const onAdd = render();
  expect(await screen.findByText("Counts for Arts/Humanities, Writing Intensive")).toBeVisible();
  await userEvent.click(screen.getByRole("button", { name: "Add SYN 2001W to plan" }));
  expect(onAdd).toHaveBeenCalledWith(expect.objectContaining({ code: "SYN 2001W" }), "Spring 2027");
  expect(screen.getByRole("status")).toHaveTextContent("SYN 2001W added to Spring 2027.");
});

it("explains when no course covers two remaining needs", async () => {
  server.use(http.get(api("/liberal-ed/double-dippers"), () => HttpResponse.json({ remaining: [], courses: [], total: 0, limit: 5, offset: 0 })));
  render();
  expect(await screen.findByText("No single course covers two of your remaining needs.")).toBeVisible();
});

it("skips double dipper suggestions when fewer than two needs remain", () => {
  render(liberal({ remaining: ["Arts/Humanities"] }));
  expect(screen.queryByRole("heading", { name: "Courses that count twice" })).not.toBeInTheDocument();
});

it("renders nothing for an API without the tracker", () => {
  const { container } = renderWithProviders(<LiberalEdPanel plan={actionPlan} courses={[]} onAdd={vi.fn()} />);
  expect(container).toBeEmptyDOMElement();
});
