import { create } from "zustand";
import type { Violation } from "@/api/client";
import type { Course, CourseStatus, TermId } from "@/api/types";

export interface DraftEntry {
  status: CourseStatus;
  term: TermId | null;
}

/** Only the edits made since the last save. Saved plan + draft = what the user sees. */
interface PlanDraftState {
  changes: Record<string, DraftEntry>;
  /** Catalog-only or newly generated courses that are not in the saved plan yet. */
  extras: Record<string, Course>;
  /** A catalog year chosen in this draft; carried into Build and Save until saved. */
  catalogTerm: TermId | null;
  violations: Violation[];
  setChanges: (changes: Record<string, DraftEntry>) => void;
  setExtras: (extras: Record<string, Course>) => void;
  selectCatalogTerm: (term: TermId | null) => void;
  setViolations: (violations: Violation[]) => void;
  clear: () => void;
}

export const usePlanDraft = create<PlanDraftState>((set) => ({
  changes: {},
  extras: {},
  catalogTerm: null,
  violations: [],
  setChanges: (changes) => set({ changes, violations: [] }),
  setExtras: (extras) => set({ extras }),
  selectCatalogTerm: (catalogTerm) => set({ catalogTerm }),
  setViolations: (violations) => set({ violations }),
  clear: () => set({ changes: {}, extras: {}, catalogTerm: null, violations: [] }),
}));
