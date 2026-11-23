import { screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { expect, it, vi } from "vitest";
import { renderWithProviders } from "@/test/render";
import { SemesterView } from "./SemesterView";
import { plannedCourse, actionPlan, actionProfile } from "@/test/planning";

it("lets current classes move directly from their semester row", async () => {
  const onAdd = vi.fn();
  const current = { ...plannedCourse, status: "prog" as const, term: actionPlan.currentTerm };
  renderWithProviders(<SemesterView plan={actionPlan} profile={actionProfile} courses={[current]} goal={24}
    onOpen={vi.fn()} onAdd={onAdd} onRemove={vi.fn()} />);
  expect(screen.getByRole("option", { name: "Fall 2026 (current)" })).toBeEnabled();
  await userEvent.selectOptions(screen.getByRole("combobox", { name: "Move TEST 1001 to semester" }), "Spring 2028");
  expect(onAdd).toHaveBeenCalledWith("TEST 1001", 4);
  expect(screen.getByRole("button", { name: "Add class to Fall 2026" })).toBeInTheDocument();
});

it("shows generated current-term suggestions without marking them enrolled", () => {
  const suggested = { ...plannedCourse, status: "plan" as const, term: actionPlan.currentTerm };
  renderWithProviders(<SemesterView plan={actionPlan} profile={actionProfile} courses={[suggested]} goal={24}
    onOpen={vi.fn()} onAdd={vi.fn()} onRemove={vi.fn()} onCredits={vi.fn()} />);
  const current = screen.getByRole("region", { name: "Fall 2026, current classes" });
  expect(within(current).getByText("TEST 1001")).toBeInTheDocument();
  expect(within(current).getByText("Planned")).toBeInTheDocument();
  expect(within(current).getByText("3 credits")).toBeInTheDocument();
});
