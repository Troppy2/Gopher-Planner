// Mock backend state. Delete this folder once the Flask API is live.
import seed from "./seed.json";
import type { Options, Plan, Profile, Summary } from "../types";

interface Db {
  profile: Profile;
  summary: Summary;
  plan: Plan;
  options: Options;
  transcript: { completed: number; inProgress: number };
}

const KEY = "gp-mock-db";
const fresh = (): Db => structuredClone(seed) as Db;

function load(): Db {
  try {
    const raw = localStorage.getItem(KEY);
    if (raw) return JSON.parse(raw) as Db;
  } catch {
    // Storage blocked or corrupt: fall back to the seed.
  }
  return fresh();
}

export let db: Db = load();

export function persist() {
  try {
    localStorage.setItem(KEY, JSON.stringify(db));
  } catch {
    // Non-fatal: the demo just won't survive a refresh.
  }
}

export function resetMockDb() {
  db = fresh();
  try {
    localStorage.removeItem(KEY);
  } catch {
    // ignore
  }
}

/** Preview switches used by the dev-only demo toggles. */
export const mockFlags = {
  failNextSettingsSave: false,
  failCatalog: false,
  nextUploadIsScan: false,
};

export const delay = (ms = 300) => new Promise((r) => setTimeout(r, ms));
