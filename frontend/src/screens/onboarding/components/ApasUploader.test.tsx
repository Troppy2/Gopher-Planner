import { http, HttpResponse } from "msw";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { api, server } from "@/test/server";
import { renderWithProviders } from "@/test/render";
import CourseworkScreen from "../CourseworkScreen";
import { useOnboarding } from "../onboarding.store";

const pdf = new File(["%PDF-1.4"], "apas.pdf", { type: "application/pdf" });

/** Node's fetch cannot send jsdom FormData, so only the multipart POST is answered at the fetch boundary. */
function stubUpload(response: () => Promise<Response>) {
  const original = globalThis.fetch;
  vi.spyOn(globalThis, "fetch").mockImplementation((input, init) =>
    String(input).endsWith("/api/v1/transcripts") && init?.method === "POST" ? response() : original(input, init));
}

function transcript(body: object) {
  server.use(
    http.get(api("/coursework"), () => HttpResponse.json({ courses: [], skipped: false })),
    http.get(api("/transcripts/t1"), () => HttpResponse.json({ id: "t1", fileName: "apas.pdf", completed: 0, inProgress: 0, courses: [], ...body })),
  );
}

async function choose(container: HTMLElement) {
  const input = container.querySelector('input[type="file"]') as HTMLInputElement;
  await userEvent.upload(input, pdf);
}

beforeEach(() => {
  useOnboarding.getState().reset();
  useOnboarding.setState({ method: "upload" });
});

describe("transcript upload states", () => {
  it("reflects the real request, then shows parsed counts and rows for correction", async () => {
    let finish: (value: Response) => void = () => {};
    stubUpload(() => new Promise((resolve) => { finish = resolve; }));
    transcript({ status: "parsed", completed: 1, inProgress: 1, courses: [
      { code: "CSCI 1133", title: "Intro", credits: 4, status: "done", term: "Fall 2025", grade: "A", source: "transcript" },
      { code: "MATH 1271", title: "Calculus", credits: 4, status: "prog", term: "Spring 2026", grade: null, source: "transcript" }] });
    const { container } = renderWithProviders(<CourseworkScreen />);
    await choose(container);
    expect(await screen.findByText(/Uploading and reading/)).toBeInTheDocument();
    expect(screen.getByText(/scanned pages can take up to a minute/i)).toBeInTheDocument();
    finish(Response.json({ id: "t1" }, { status: 201 }));
    expect(await screen.findByText("We found 1 completed and 1 in-progress courses.")).toBeInTheDocument();
    expect(screen.getByText("CSCI 1133")).toBeInTheDocument();
    expect(screen.getByText("MATH 1271")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Correct these courses" }));
    expect(useOnboarding.getState().method).toBe("manual");
    expect(useOnboarding.getState().manual.map((course) => course.code)).toEqual(["CSCI 1133", "MATH 1271"]);
  });

  it("lists course codes that could not be imported so they can be added by hand", async () => {
    stubUpload(async () => Response.json({ id: "t1" }, { status: 201 }));
    transcript({ status: "parsed", completed: 1, notImported: ["HUM 1T001"], courses: [
      { code: "CSCI 1133", title: "Intro", credits: 4, status: "done", term: "Fall 2025", grade: "A", source: "transcript" }] });
    const { container } = renderWithProviders(<CourseworkScreen />);
    await choose(container);
    expect(await screen.findByText(/1 course couldn't be imported/i)).toBeInTheDocument();
    expect(screen.getByText(/HUM 1T001/)).toBeInTheDocument();
  });

  it("explains that even text recognition found nothing and offers manual entry, with no retry", async () => {
    stubUpload(async () => Response.json({ id: "t1" }, { status: 201 }));
    transcript({ status: "no_text" });
    const { container } = renderWithProviders(<CourseworkScreen />);
    await choose(container);
    expect(await screen.findByText(/even with text recognition/i)).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /text recognition/i })).not.toBeInTheDocument();
    await userEvent.click(screen.getAllByRole("button", { name: "Enter courses manually" })[0]);
    expect(useOnboarding.getState().method).toBe("manual");
  });

  it("gives a failed parse its own state with a manual-entry path", async () => {
    stubUpload(async () => Response.json({ id: "t1" }, { status: 201 }));
    transcript({ status: "failed", errorCode: "unrecognized_format" });
    const { container } = renderWithProviders(<CourseworkScreen />);
    await choose(container);
    expect(await screen.findByText("We couldn't find any courses in this PDF.")).toBeInTheDocument();
    expect(screen.queryByText("Reading your courses")).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Enter courses manually" })).toBeInTheDocument();
  });

  it("shows a rejected upload", async () => {
    stubUpload(async () => Response.json({ error: "Only PDF files are accepted", code: "not_a_pdf" }, { status: 415 }));
    transcript({ status: "parsed" });
    const { container } = renderWithProviders(<CourseworkScreen />);
    await choose(container);
    expect(await screen.findByText(/Only PDF files are accepted/)).toBeInTheDocument();
  });
});
