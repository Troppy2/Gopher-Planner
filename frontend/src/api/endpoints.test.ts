import { http, HttpResponse } from "msw";
import { describe, expect, it, vi } from "vitest";
import { api, server } from "@/test/server";
import { ApiError } from "./client";
import { getOptions } from "./endpoints";
import {
  generatePlan,
  getCoursework,
  getPlan,
  getSummary,
  getTranscript,
  saveCoursework,
  savePlan,
  uploadTranscript,
} from "./endpoints";

interface Seen {
  method?: string;
  url?: string;
  body?: unknown;
  credentials?: string;
  contentType?: string | null;
}

function capture(method: "get" | "put" | "post", path: string, response: unknown, status = 200) {
  const seen: Seen = {};
  server.use(
    http[method](api(path), async ({ request }) => {
      seen.method = request.method;
      seen.url = new URL(request.url).pathname;
      seen.credentials = request.credentials;
      seen.contentType = request.headers.get("Content-Type");
      const text = request.method === "GET" ? "" : await request.clone().text();
      seen.body = text && seen.contentType?.includes("json") ? JSON.parse(text) : text;
      return HttpResponse.json(response as object, { status });
    }),
  );
  return seen;
}

async function rejection(promise: Promise<unknown>) {
  try {
    await promise;
  } catch (error) {
    return error as ApiError;
  }
  throw new Error("Expected the request to fail");
}

const plan = { terms: ["Completed", "Fall 2026"], currentTerm: "Fall 2026", baseCredits: 0, courses: [],
  catalogTerm: null, availableCatalogTerms: ["Fall 2026"], warnings: ["program_version_unconfirmed"], requirementProgress: [] };

describe("API endpoints", () => {
  it("reports a failed program list instead of silently hiding supported majors", async () => {
    capture("get", "/programs", { error: "Unavailable" }, 503);
    await expect(getOptions()).rejects.toBeInstanceOf(ApiError);
  });
  it("getSummary reads the real summary with credentials", async () => {
    const summary = { gpa: null, gradedCredits: 0, creditsCompleted: 0, creditsTotal: 120, percentComplete: null, program: "", source: "" };
    const seen = capture("get", "/summary", summary);
    const spy = vi.spyOn(globalThis, "fetch");
    await expect(getSummary()).resolves.toEqual(summary);
    expect(seen).toMatchObject({ method: "GET", url: "/api/v1/summary" });
    expect(spy.mock.calls[0][1]).toMatchObject({ credentials: "include" });
  });

  it("getPlan returns the v2 plan fields", async () => {
    capture("get", "/plan", plan);
    await expect(getPlan()).resolves.toEqual(plan);
  });

  it("savePlan sends changes and the selected catalog term", async () => {
    const seen = capture("put", "/plan", plan);
    await savePlan([{ code: "CSCI 2041", status: "plan", term: "Spring 2027" }], "Fall 2026");
    expect(seen).toMatchObject({ method: "PUT", body: { changes: [{ code: "CSCI 2041", status: "plan", term: "Spring 2027" }], catalogTerm: "Fall 2026" } });
    await savePlan([]);
    expect(seen.body).toEqual({ changes: [] });
  });

  it("savePlan maps a 409 to a validation error with violations", async () => {
    const violations = [{ code: "CSCI 2041", reason: "prerequisite_not_before", detail: "CSCI 1933" }];
    capture("put", "/plan", { error: "The resulting plan breaks a scheduling rule", code: "plan_invalid", violations }, 409);
    const error = await rejection(savePlan([]));
    expect(error).toBeInstanceOf(ApiError);
    expect([error.code, error.serverCode, error.message, error.violations]).toEqual(
      ["validation", "plan_invalid", "The resulting plan breaks a scheduling rule", violations]);
  });

  it("generatePlan posts dry runs and catalog terms and returns the envelope", async () => {
    const envelope = { jobId: "job", status: "succeeded", warnings: [], plan };
    const seen = capture("post", "/plans/generate", envelope);
    await expect(generatePlan({ dryRun: true, catalogTerm: "Fall 2026" })).resolves.toEqual(envelope);
    expect(seen.body).toEqual({ dryRun: true, catalogTerm: "Fall 2026" });
    await generatePlan();
    expect(seen.body).toEqual({ dryRun: false });
  });

  it("getCoursework and saveCoursework use the coursework contract", async () => {
    const body = { courses: [{ code: "CSCI 1133", title: "Intro", credits: 4, status: "done", term: null, grade: null }], skipped: false };
    capture("get", "/coursework", body);
    await expect(getCoursework()).resolves.toEqual(body);
    const seen = capture("put", "/coursework", body);
    await saveCoursework({ courses: [], skipped: true });
    expect(seen).toMatchObject({ method: "PUT", body: { courses: [], skipped: true } });
  });

  it("uploadTranscript sends multipart form data without a manual content type", async () => {
    // Node's fetch cannot serialize jsdom's FormData, so assert the request the browser would send.
    const spy = vi.spyOn(globalThis, "fetch").mockResolvedValue(HttpResponse.json({ id: "t1" }, { status: 201 }));
    const file = new File(["%PDF-1.4"], "apas.pdf", { type: "application/pdf" });
    await expect(uploadTranscript(file)).resolves.toEqual({ id: "t1" });
    const [url, init] = spy.mock.calls[0] as [string, RequestInit];
    expect(new URL(url).pathname).toBe("/api/v1/transcripts");
    expect(init.method).toBe("POST");
    expect(init.credentials).toBe("include");
    expect((init.body as FormData).get("file")).toBe(file);
    expect(Object.keys(init.headers as Record<string, string>).map((key) => key.toLowerCase())).not.toContain("content-type");
  });

  it("getTranscript returns parsed rows", async () => {
    const transcript = { id: "t1", fileName: "apas.pdf", status: "no_text", completed: 0, inProgress: 0, courses: [] };
    capture("get", "/transcripts/t1", transcript);
    await expect(getTranscript("t1")).resolves.toEqual(transcript);
  });

  it("maps 401, 400, 404, 5xx and network failures", async () => {
    capture("get", "/summary", { error: "Not signed in" }, 401);
    expect((await rejection(getSummary())).code).toBe("auth");
    capture("get", "/summary", { error: "Bad input", code: "invalid_change" }, 400);
    const invalid = await rejection(getSummary());
    expect([invalid.code, invalid.message]).toEqual(["validation", "Bad input"]);
    capture("get", "/summary", { error: "Missing", code: "unknown_course" }, 404);
    expect((await rejection(getSummary())).code).toBe("not_found");
    capture("get", "/summary", { error: "Boom", code: "generation_failed" }, 500);
    expect((await rejection(getSummary())).code).toBe("network");
    server.use(http.get(api("/summary"), () => HttpResponse.error()));
    expect((await rejection(getSummary())).code).toBe("network");
  });
});
