// Every screen reads data through these functions. They currently resolve from the
// mock DB; replace each body with a call to `api/client.ts` when the backend is ready.
import { db, delay, mockFlags, persist } from "./mock/mockDb";
import { ApiError } from "./client";
import type { Course, CourseFilters, Options, Plan, PlanChange, Profile, Summary, Transcript } from "./types";

const clone = <T>(v: T): T => structuredClone(v);

/** GET /api/v1/summary */
export async function getSummary(): Promise<Summary> {
  await delay();
  return clone(db.summary);
}

/** GET /api/v1/profile */
export async function getProfile(): Promise<Profile> {
  await delay(150);
  return clone(db.profile);
}

/** PUT /api/v1/profile */
export async function updateProfile(patch: Partial<Profile>): Promise<Profile> {
  await delay(800);
  if (mockFlags.failNextSettingsSave) {
    mockFlags.failNextSettingsSave = false;
    throw new ApiError("network", "Could not reach the server.");
  }
  db.profile = { ...db.profile, ...patch };
  db.summary.program = db.profile.major;
  persist();
  return clone(db.profile);
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

const levelOf = (code: string) => code.match(/\d/)?.[0] ?? "";

/** GET /api/v1/courses */
export async function getCourses(f: CourseFilters = {}): Promise<Course[]> {
  await delay(450);
  if (mockFlags.failCatalog) throw new ApiError("network", "Catalog data could not be loaded.");
  const q = f.q?.trim().toLowerCase() ?? "";
  return clone(
    db.plan.courses.filter((c) => {
      if (q && !`${c.code} ${c.title} ${c.professors.join(" ")}`.toLowerCase().includes(q)) return false;
      if (f.subject && !c.code.startsWith(f.subject + " ")) return false;
      if (f.level && levelOf(c.code) !== f.level[0]) return false;
      if (f.credits === "1 to 2" && c.credits > 2) return false;
      if (f.credits === "3" && c.credits !== 3) return false;
      if (f.credits === "4 or more" && c.credits < 4) return false;
      if (f.term && !c.offered.includes(f.term as Course["offered"][number])) return false;
      if (f.requirement && c.requirement !== f.requirement) return false;
      const nextTerm = c.offered.includes("Spring");
      if (f.availability === "Offered next term" && !nextTerm) return false;
      if (f.availability === "Not offered next term" && nextTerm) return false;
      return true;
    }),
  );
}

/** GET /api/v1/courses/:code */
export async function getCourse(code: string): Promise<Course | null> {
  await delay(150);
  return clone(db.plan.courses.find((c) => c.code === code) ?? null);
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
