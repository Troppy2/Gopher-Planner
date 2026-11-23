import { http, HttpResponse } from "msw";
import { describe, expect, it, vi } from "vitest";
import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { api, server } from "@/test/server";
import { renderWithProviders } from "@/test/render";
import { CourseworkEditor, termOptions } from "./CourseworkEditor";

const saved = {
  skipped: false,
  courses: [
    { code: "CSCI 1133", title: "Intro", credits: 4, status: "done", term: "Fall 2025", grade: "A", source: "transcript" },
    { code: "MATH 1271", title: "Calculus", credits: 4, status: "prog", term: "Fall 2026", grade: null, source: "manual" },
  ],
};

describe("CourseworkEditor", () => {
  it("restores uploaded coursework after all saved courses were deleted", async () => {
    let courses = saved.courses;
    server.use(http.get(api("/coursework"), () => HttpResponse.json({ skipped: false, courses })),
      http.put(api("/coursework"), async ({ request }) => {
        const body = await request.json() as typeof saved;
        courses = body.courses;
        return HttpResponse.json(body);
      }),
      http.post(api("/transcripts"), () => { courses = saved.courses; return HttpResponse.json({ id: "restored" }, { status: 201 }); }),
      http.get(api("/transcripts/restored"), () => HttpResponse.json({ id: "restored", fileName: "synthetic.pdf", status: "parsed", completed: 1, inProgress: 1, courses })));
    const { container } = renderWithProviders(<CourseworkEditor />);
    await screen.findByText("CSCI 1133");
    await userEvent.click(screen.getByRole("button", { name: "Remove CSCI 1133" }));
    await userEvent.click(screen.getByRole("button", { name: "Remove MATH 1271" }));
    await waitFor(() => expect(courses).toEqual([]), { timeout: 3000 });
    await waitFor(() => expect(screen.queryByText("Saving…")).not.toBeInTheDocument());
    await userEvent.upload(container.querySelector('input[type="file"]') as HTMLInputElement, new File(["%PDF-1.4 synthetic"], "synthetic.pdf", { type: "application/pdf" }));
    expect(await screen.findByText("Imported 1 completed and 1 in-progress courses.")).toBeInTheDocument();
    expect(await screen.findByText("CSCI 1133")).toBeInTheDocument();
    expect(screen.queryByText("Saving…")).not.toBeInTheDocument();
  });
  it("removes a course and saves the whole edited set", async () => {
    let body: unknown = null;
    server.use(
      http.get(api("/coursework"), () => HttpResponse.json(saved)),
      http.put(api("/coursework"), async ({ request }) => {
        const submitted = await request.json() as typeof saved;
        body = submitted;
        return HttpResponse.json(submitted);
      }),
    );
    renderWithProviders(<CourseworkEditor />);
    expect(await screen.findByText("CSCI 1133")).toBeInTheDocument();
    expect(screen.queryByText("Saving…")).not.toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Remove MATH 1271" }));
    expect(screen.queryByText("MATH 1271")).toBeNull();
    await waitFor(() => expect(body).toEqual({ skipped: false, courses: [saved.courses[0]] }), { timeout: 3000 });
    await waitFor(() => expect(screen.queryByText("Saving…")).not.toBeInTheDocument());
  });

  it("re-uploads an APAS PDF and reports what was not imported", async () => {
    server.use(
      http.get(api("/coursework"), () => HttpResponse.json(saved)),
      http.get(api("/transcripts/t9"), () =>
        HttpResponse.json({ id: "t9", fileName: "apas.pdf", status: "parsed", completed: 3, inProgress: 2, courses: [], notImported: ["HUM 1T001"] })),
    );
    const original = globalThis.fetch;
    vi.spyOn(globalThis, "fetch").mockImplementation((input, init) =>
      String(input).endsWith("/api/v1/transcripts") && init?.method === "POST"
        ? Promise.resolve(Response.json({ id: "t9" }, { status: 201 }))
        : original(input, init));
    const { container } = renderWithProviders(<CourseworkEditor />);
    await screen.findByText("CSCI 1133");
    const input = container.querySelector('input[type="file"]') as HTMLInputElement;
    await userEvent.upload(input, new File(["%PDF-1.4"], "apas.pdf", { type: "application/pdf" }));
    expect(await screen.findByText("Imported 3 completed and 2 in-progress courses.")).toBeInTheDocument();
    expect(screen.getByText(/HUM 1T001/)).toBeInTheDocument();
  });

  it("offers recent terms including summer", () => {
    expect(termOptions(new Date(2026, 10, 23)).slice(0, 4)).toEqual(["Fall 2027", "Summer 2027", "Spring 2027", "Fall 2026"]);
  });
});
