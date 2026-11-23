// Remaining mock state. Only select options are still mocked (issue #9); coursework, summary,
// plan, generation and transcripts use the real API. Delete this folder once options are live.
import seed from "./seed.json";
import type { Options } from "../types";

interface Db {
  options: Options;
}

// Bump when seed.json changes shape so stale browser copies are replaced.
const KEY = "gp-mock-db-v2";
const fresh = (): Db => ({ options: structuredClone(seed.options) as Options });

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
