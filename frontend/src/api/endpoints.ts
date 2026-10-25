// Every screen reads data through these functions. They currently resolve from the
// mock DB; replace each body with a call to `api/client.ts` when the backend is ready.
import { db, delay, mockFlags, persist } from "./mock/mockDb";
import { ApiError } from "./client";
import type {
  CatalogCourse,
  CatalogCoursePage,
  CourseFilters,
  Options,
  Plan,
  PlanChange,
  Profile,
  Summary,
  Transcript,
} from "./types";

const clone = <T>(v: T): T => structuredClone(v);

/** GET /api/v1/summary */
export async function getSummary(): Promise<Summary> {
  await delay();
  return clone(db.summary);
}

/** GET /api/v1/profile */
export async function getProfile(): Promise<Profile> {
  const response = await fetch("/api/v1/profile", {
    method: "GET",
    credentials: "include",
    headers: {
      Accept: "application/json",
    },
  });

  if (!response.ok) {
    if (response.status === 401) {
      throw new ApiError("auth", "You must be signed in to view your profile.");
    }

    throw new ApiError("network", "Could not load your profile.");
  }

  return response.json() as Promise<Profile>;
}

/** PUT /api/v1/profile */
export async function updateProfile(
  patch: Partial<Profile>,
): Promise<Profile> {
  const response = await fetch("/api/v1/profile", {
    method: "PUT",
    credentials: "include",
    headers: {
      Accept: "application/json",
      "Content-Type": "application/json",
    },
    body: JSON.stringify(patch),
  });

  if (!response.ok) {
    if (response.status === 401) {
      throw new ApiError("auth", "You must be signed in to update your profile.");
    }

    if (response.status === 400) {
      const error = await response.json().catch(() => null);
      throw new ApiError(
        "validation",
        error?.error ?? "The profile information is invalid.",
      );
    }

    throw new ApiError("network", "Could not save your profile.");
  }

  return response.json() as Promise<Profile>;
}

/** Select options (majors, standings, terms). Likely part of GET /programs later. */
export async function getOptions(): Promise<Options> {
  await delay(100);
  return clone(db.options);
}

/** GET /api/v1/plan */
export async function getPlan(): Promise<Plan> {
  await delay();
  return clone(db.plan);
}

/** PUT /api/v1/plan */
export async function savePlan(changes: PlanChange[]): Promise<Plan> {
  await delay(600);
  for (const ch of changes) {
    const c = db.plan.courses.find((x) => x.code === ch.code);
    if (c) Object.assign(c, { status: ch.status, term: ch.term });
  }
  persist();
  return clone(db.plan);
}

/** POST /api/v1/plans/generate. The real API returns a job id to poll. */
export async function generatePlan(): Promise<{ jobId: string }> {
  await delay(200);
  return { jobId: "mock-job" };
}

/** GET /api/v1/courses */
export async function getCourses(
  filters: CourseFilters = {},
): Promise<CatalogCoursePage> {
  const params = new URLSearchParams();

  if (filters.q?.trim()) params.set("q", filters.q.trim());
  if (filters.subject) params.set("subject", filters.subject);

  // The UI uses labels like "1xxx"; the API expects the leading digit.
  if (filters.level) {
    params.set("level", filters.level.match(/^\d/)?.[0] ?? filters.level);
  }

  if (filters.credits) params.set("credits", filters.credits);
  if (filters.term) params.set("term", filters.term);

  // Friendly requirement labels aren't raw SQLite requirement codes.
  // Do not send them until a proper mapping exists.
  if (filters.availability) {
    params.set("availability", filters.availability);
  }

  // Server-side pagination.
  const limit = Math.min(100, Math.max(1, filters.limit ?? 25));
  const offset = Math.max(0, filters.offset ?? 0);

  params.set("limit", String(limit));
  params.set("offset", String(offset));

  const response = await fetch(`/api/v1/courses?${params.toString()}`, {
    credentials: "include",
    headers: { Accept: "application/json" },
  });

  if (!response.ok) {
    throw new ApiError(
      "network",
      response.status === 503
        ? "The course catalog is temporarily unavailable."
        : "Catalog data could not be loaded.",
    );
  }

  return (await response.json()) as CatalogCoursePage;
}

/** GET /api/v1/courses/:code */
export async function getCatalogCourse(code: string): Promise<CatalogCourse> {
  const response = await fetch(`/api/v1/courses/${encodeURIComponent(code)}`, {
    credentials: "include",
    headers: { Accept: "application/json" },
  });

  if (!response.ok) {
    throw new ApiError(
      "network",
      response.status === 404
        ? "This course was not found in the catalog."
        : response.status === 503
          ? "The course catalog is temporarily unavailable."
          : "Course details could not be loaded.",
    );
  }

  return (await response.json()) as CatalogCourse;
}

const transcripts = new Map<string, Transcript & { readyAt: number }>();

/** POST /api/v1/transcripts (multipart PDF) */
export async function uploadTranscript(file: File): Promise<{ id: string }> {
  await delay(200);
  const id = `t-${Date.now()}`;
  transcripts.set(id, {
    id,
    fileName: file.name,
    status: "parsing",
    completed: 0,
    inProgress: 0,
    readyAt: Date.now() + 1400,
  });
  return { id };
}

/** GET /api/v1/transcripts/:id. Poll while status is "parsing". */
export async function getTranscript(id: string): Promise<Transcript> {
  await delay(100);
  const t = transcripts.get(id);
  if (!t) throw new ApiError("not_found", "Transcript not found.");
  if (t.status === "parsing" && Date.now() >= t.readyAt) {
    if (mockFlags.nextUploadIsScan) {
      t.status = "no_text";
    } else {
      Object.assign(t, { status: "parsed", ...db.transcript });
    }
  }
  const { readyAt: _readyAt, ...rest } = t;
  return rest;
}

/** POST /api/v1/transcripts/:id/ocr */
export async function retryTranscriptOcr(id: string): Promise<void> {
  await delay(200);
  const t = transcripts.get(id);
  if (!t) throw new ApiError("not_found", "Transcript not found.");
  mockFlags.nextUploadIsScan = false;
  Object.assign(t, { status: "parsing", readyAt: Date.now() + 1800 });
}
