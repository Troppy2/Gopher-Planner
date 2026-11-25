import { http, HttpResponse } from "msw";
import { beforeEach, expect, it } from "vitest";
import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { api, server } from "@/test/server";
import { renderWithProviders } from "@/test/render";
import { queryKeys } from "@/api/queryKeys";
import { usePlanDraft } from "@/features/plan/plan.store";
import SettingsScreen from "./SettingsScreen";

const options = (majors: string[]) => ({ majors, unverifiedMajors: majors, standings: ["Freshman", "Sophomore", "Junior", "Senior"],
  graduationTargets: ["Spring 2030"], subjects: [], careers: {} });

beforeEach(() => usePlanDraft.getState().clear());

it("refreshes the plan and clears the old major draft when switching majors and back", async () => {
  let profile = { name: "Synthetic Student", major: "Synthetic Alpha B.S.", standing: "Freshman", careerGoals: "", creditLoad: 15, graduationTarget: "Spring 2030", onboarded: true };
  server.use(
    http.get(api("/profile"), () => HttpResponse.json(profile)),
    http.put(api("/profile"), async ({ request }) => { profile = { ...profile, ...await request.json() as object }; return HttpResponse.json(profile); }),
    http.get(api("/options"), () => HttpResponse.json(options(["Synthetic Alpha B.S.", "Synthetic Beta B.S."]))),
    http.get(api("/coursework"), () => HttpResponse.json({ courses: [], skipped: false })),
  );
  const { client } = renderWithProviders(<SettingsScreen />);
  const major = await screen.findByRole("combobox", { name: "Major or degree program" });
  for (const name of ["Synthetic Beta B.S.", "Synthetic Alpha B.S."]) {
    client.setQueryData(queryKeys.plan, { courses: [] });
    client.setQueryData(queryKeys.summary, {});
    usePlanDraft.getState().selectCatalogTerm("Fall 2026");
    await userEvent.clear(major);
    await userEvent.type(major, name);
    await userEvent.click(await screen.findByRole("option", { name }));
    await waitFor(() => expect(profile.major).toBe(name), { timeout: 3000 });
    await waitFor(() => expect(client.getQueryState(queryKeys.plan)?.isInvalidated).toBe(true));
    expect(client.getQueryState(queryKeys.summary)?.isInvalidated).toBe(true);
    expect(usePlanDraft.getState().catalogTerm).toBeNull();
  }
});

it("lets users retry a failed major list", async () => {
  let available = false;
  server.use(
    http.get(api("/profile"), () => HttpResponse.json({ name: "Synthetic Student", major: "Synthetic Alpha B.S.", standing: "Freshman", careerGoals: "", creditLoad: 15, graduationTarget: "Spring 2030", onboarded: true })),
    http.put(api("/profile"), async ({ request }) => HttpResponse.json({ ...await request.json() as object, onboarded: true })),
    http.get(api("/options"), () => available ? HttpResponse.json(options(["Synthetic Beta B.S."])) : HttpResponse.json({ error: "Unavailable" }, { status: 503 })),
    http.get(api("/coursework"), () => HttpResponse.json({ courses: [], skipped: false })),
  );
  renderWithProviders(<SettingsScreen />);
  expect(await screen.findByText("Could not load the major list.")).toBeVisible();
  available = true;
  await userEvent.click(screen.getByRole("button", { name: "Retry major list" }));
  await userEvent.clear(screen.getByRole("combobox", { name: "Major or degree program" }));
  expect(await screen.findByRole("option", { name: "Synthetic Beta B.S." })).toBeVisible();
  await userEvent.click(screen.getByRole("option", { name: "Synthetic Beta B.S." }));
  await waitFor(() => expect(screen.queryByText("Saving…")).not.toBeInTheDocument(), { timeout: 3000 });
});
