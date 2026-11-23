import { describe, expect, it, vi } from "vitest";
import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { renderWithProviders } from "@/test/render";
import { PlanCourseActions } from "./PlanCourseActions";
import { http, HttpResponse } from "msw";
import { api, server } from "@/test/server";

import { plannedCourse, actionPlan, actionProfile } from "@/test/planning";

describe("planned course actions", () => {
  it("requests every slot category and loads later result pages", async () => {
    server.use(http.get(api("/courses"), ({ request }) => {
      const params = new URL(request.url).searchParams;
      expect(params.getAll("le")).toEqual(["Synthetic arts", "Synthetic history"]);
      const offset = Number(params.get("offset"));
      return HttpResponse.json({ courses: offset ? [{ code: "TEST 1002", title: "Later synthetic result", minimumCredits: 3,
        offered: ["Spring"], leAttributes: ["Synthetic arts", "Synthetic history"], prerequisites: { status: "none", requirements: null } }] : [],
        total: 101, offset, limit: 100 });
    }));
    renderWithProviders(<PlanCourseActions course={{ ...plannedCourse, slot: "Synthetic breadth", slotCategories: ["Synthetic arts", "Synthetic history"] }}
      courses={[plannedCourse]} plan={actionPlan} profile={actionProfile} onMove={vi.fn()} onRemove={vi.fn()} onSwap={vi.fn()} announce={vi.fn()} />);
    await userEvent.click(screen.getByRole("button", { name: "Swap suggestion" }));
    await userEvent.click(await screen.findByRole("button", { name: "More suggestions" }));
    expect(await screen.findByRole("button", { name: /Later synthetic result/ })).toBeEnabled();
  });
  it("loads alternatives by category and swaps a valid suggestion", async () => {
    const onSwap = vi.fn();
    server.use(http.get(api("/courses"), ({ request }) => {
      expect(new URL(request.url).searchParams.get("le")).toBe("Synthetic arts");
      return HttpResponse.json({ courses: [{ code: "TEST 1002", title: "Synthetic replacement", minimumCredits: 3,
        offered: ["Spring"], leAttributes: ["Synthetic arts"], prerequisites: { status: "none", requirements: null } }], total: 1 });
    }));
    renderWithProviders(<PlanCourseActions course={{ ...plannedCourse, slot: "Synthetic arts", slotCategories: ["Synthetic arts"] }}
      courses={[plannedCourse]} plan={actionPlan} profile={actionProfile} onMove={vi.fn()} onRemove={vi.fn()} onSwap={onSwap} announce={vi.fn()} />);
    await userEvent.click(screen.getByRole("button", { name: "Swap suggestion" }));
    await userEvent.click(await screen.findByRole("button", { name: /TEST 1002: Synthetic replacement/ }));
    expect(onSwap).toHaveBeenCalledWith("TEST 1001", expect.objectContaining({ code: "TEST 1002" }));
  });
  it("disables invalid terms with a reason and supports keyboard moves and removal", async () => {
    const onMove = vi.fn(), onRemove = vi.fn(), onSwap = vi.fn(), announce = vi.fn();
    renderWithProviders(<PlanCourseActions course={plannedCourse} courses={[plannedCourse]} plan={actionPlan} profile={actionProfile}
      onMove={onMove} onRemove={onRemove} onSwap={onSwap} announce={announce} />);
    expect(screen.getByRole("option", { name: /Fall 2027.*Not offered/ })).toBeDisabled();
    const move = screen.getByRole("combobox", { name: "Move TEST 1001 to semester" });
    await userEvent.selectOptions(move, "Spring 2028");
    expect(onMove).toHaveBeenCalledWith("TEST 1001", "Spring 2028");
    expect(announce).toHaveBeenCalledWith("TEST 1001 moved to Spring 2028.");
    await userEvent.click(screen.getByRole("button", { name: "Remove from plan" }));
    expect(onRemove).toHaveBeenCalledWith("TEST 1001");
  });
});
