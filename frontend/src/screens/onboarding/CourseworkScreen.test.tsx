import { http, HttpResponse } from "msw";
import { beforeEach, describe, expect, it } from "vitest";
import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { api, server } from "@/test/server";
import type { Coursework } from "@/api/types";
import { renderWithProviders } from "@/test/render";
import CourseworkScreen from "./CourseworkScreen";
import { toCourseworkEntries } from "./coursework";
import { useOnboarding } from "./onboarding.store";

const empty: Coursework = { courses: [], skipped: false };

function stubCoursework(initial: Coursework = empty) {
  const saved: unknown[] = [];
  server.use(
    http.get(api("/coursework"), () => HttpResponse.json(initial)),
    http.put(api("/coursework"), async ({ request }) => {
      const body = await request.json();
      saved.push(body);
      return HttpResponse.json(body as object);
    }),
  );
  return saved;
}

beforeEach(() => useOnboarding.getState().reset());

describe("toCourseworkEntries", () => {
  it("maps completed courses to an unknown term and in-progress courses to the current term", () => {
    expect(toCourseworkEntries([
      { code: "CSCI 1133", title: "Intro", credits: 4, status: "done" },
      { code: "MATH 1271", title: "Calculus", credits: 4, status: "prog" },
    ], "Fall 2026")).toEqual([
      { code: "CSCI 1133", title: "Intro", credits: 4, status: "done", term: null, grade: null },
      { code: "MATH 1271", title: "Calculus", credits: 4, status: "prog", term: "Fall 2026", grade: null },
    ]);
  });

  it("keeps the term and grade of a corrected transcript course", () => {
    expect(toCourseworkEntries([
      { code: "CSCI 1133", title: "Intro", credits: 4, status: "done", term: "Fall 2025", grade: "A" },
      { code: "MATH 1271", title: "Calculus", credits: 4, status: "prog", term: "Spring 2026", grade: "B" },
    ], "Fall 2026")).toEqual([
      { code: "CSCI 1133", title: "Intro", credits: 4, status: "done", term: "Fall 2025", grade: "A" },
      { code: "MATH 1271", title: "Calculus", credits: 4, status: "prog", term: "Fall 2026", grade: null },
    ]);
  });
});

describe("CourseworkScreen", () => {
  it("saves manual entries before continuing", async () => {
    const saved = stubCoursework();
    useOnboarding.setState({ method: "manual", manual: [
      { code: "CSCI 1133", title: "Intro", credits: 4, status: "done" },
      { code: "MATH 1271", title: "Calculus", credits: 4, status: "prog" },
    ] });
    renderWithProviders(<CourseworkScreen />);
    await userEvent.click(await screen.findByRole("button", { name: "Continue" }));
    await screen.findByText("Navigated away");
    expect(saved).toHaveLength(1);
    const body = saved[0] as { courses: { code: string; term: string | null; credits: number }[]; skipped: boolean };
    expect(body.skipped).toBe(false);
    expect(body.courses.map((course) => [course.code, course.credits, course.term === null])).toEqual([["CSCI 1133", 4, true], ["MATH 1271", 4, false]]);
  });

  it("records an explicit skip", async () => {
    const saved = stubCoursework();
    useOnboarding.setState({ method: "skip" });
    renderWithProviders(<CourseworkScreen />);
    await userEvent.click(await screen.findByRole("button", { name: "Continue" }));
    await screen.findByText("Navigated away");
    expect(saved).toEqual([{ courses: [], skipped: true }]);
  });

  it("shows an error and stays on the step when saving fails", async () => {
    server.use(
      http.get(api("/coursework"), () => HttpResponse.json(empty)),
      http.put(api("/coursework"), () => HttpResponse.json({ error: "Invalid course code", code: "invalid_coursework" }, { status: 400 })),
    );
    useOnboarding.setState({ method: "manual", manual: [{ code: "CSCI 1133", title: "Intro", credits: 4, status: "done" }] });
    renderWithProviders(<CourseworkScreen />);
    await userEvent.click(await screen.findByRole("button", { name: "Continue" }));
    expect(await screen.findByText(/Invalid course code/)).toBeInTheDocument();
    expect(screen.queryByText("Navigated away")).not.toBeInTheDocument();
  });

  it("restores saved manual entries after a refresh", async () => {
    stubCoursework({ courses: [{ code: "STAT 3021", title: "Statistics", credits: 3, status: "done", term: null, grade: null, source: "manual" }], skipped: false });
    renderWithProviders(<CourseworkScreen />);
    expect(await screen.findByText("STAT 3021")).toBeInTheDocument();
    await waitFor(() => expect(useOnboarding.getState().method).toBe("manual"));
  });
});
