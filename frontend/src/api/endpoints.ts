// Every screen reads data through these functions. All planner features use the real API
// through `apiRequest`. Only `getOptions` still reads mock data (issue #9).
import { db, delay } from "./mock/mockDb";
import { ApiError, apiRequest, apiUrl } from "./client";
import type {
  CatalogCourse,
  CatalogCoursePage,
  Coursework,
  CourseFilters,
  GenerateResult,
  Options,
  Plan,
  PlanChange,
  Profile,
  ProgramSummary,
  Summary,
  TermId,
  Transcript,
} from "./types";

const clone = <T>(v: T): T => structuredClone(v);

/** GET /api/v1/summary */
export const getSummary = () => apiRequest<Summary>("/summary");

/** GET /api/v1/profile */
export async function getProfile(): Promise<Profile> {
  const response = await fetch(apiUrl("/profile"), {
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
  const response = await fetch(apiUrl("/profile"), {
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

/** GET /api/v1/programs: every supported program version, without requirement details. */
export const getPrograms = () => apiRequest<{ programs: ProgramSummary[] }>("/programs");

/**
 * Select options. Standings, graduation targets, subjects and careers are still mock data
 * until a real options endpoint exists (issue #9). Majors come from the supported program
 * files so every undergraduate major can be selected.
 */
export async function getOptions(): Promise<Options> {
  await delay(100);
  const options = clone(db.options);
  try {
    const { programs } = await getPrograms();
    if (programs.length) {
      options.majors = programs.map((program) => program.name);
      options.unverifiedMajors = programs.filter((program) => !program.reviewed).map((program) => program.name);
    }
  } catch {
    // Keep the bundled list when the program listing is unavailable.
  }
  return options;
}

/** GET /api/v1/coursework */
export const getCoursework = () => apiRequest<Coursework>("/coursework");

/** PUT /api/v1/coursework: replaces the whole set. */
export const saveCoursework = (body: Coursework) =>
  apiRequest<Coursework>("/coursework", { method: "PUT", json: body });

/** GET /api/v1/plan */
export const getPlan = () => apiRequest<Plan>("/plan");

/** PUT /api/v1/plan. Pass the selected catalog term whenever a version was chosen. */
export const savePlan = (changes: PlanChange[], catalogTerm?: TermId | null) =>
  apiRequest<Plan>("/plan", { method: "PUT", json: catalogTerm ? { changes, catalogTerm } : { changes } });

/** POST /api/v1/plans/generate. Dry runs return a draft without saving. */
export const generatePlan = (options: { dryRun?: boolean; catalogTerm?: TermId | null } = {}) =>
  apiRequest<GenerateResult>("/plans/generate", {
    method: "POST",
    json: {
      dryRun: options.dryRun ?? false,
      ...(options.catalogTerm ? { catalogTerm: options.catalogTerm } : {}),
    },
  });

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
  for (const category of typeof filters.le === "string" ? [filters.le] : filters.le ?? []) params.append("le", category);

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

  const response = await fetch(apiUrl(`/courses?${params.toString()}`), {
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
  const response = await fetch(apiUrl(`/courses/${encodeURIComponent(code)}`), {
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

/**
 * POST /api/v1/transcripts (multipart PDF). The browser sets the multipart content type.
 * Scanned PDFs are read with text recognition during this request, so it can take up to a minute.
 */
export function uploadTranscript(file: File): Promise<{ id: string }> {
  const form = new FormData();
  form.append("file", file);
  return apiRequest<{ id: string }>("/transcripts", { method: "POST", form });
}

/** GET /api/v1/transcripts/:id */
export const getTranscript = (id: string) => apiRequest<Transcript>(`/transcripts/${encodeURIComponent(id)}`);
