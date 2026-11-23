import { create } from "zustand";
import type { Violation } from "@/api/client";
import type { Course, CourseStatus, TermId } from "@/api/types";

export interface DraftEntry {
  status: CourseStatus;
  term: TermId | null;
  slot?: string | null;
  credits?: number;
}

/** Only the edits made since the last save. Saved plan + draft = what the user sees. */
interface PlanDraftState {
  changes: Record<string, DraftEntry>;
  /** Catalog-only or newly generated courses that are not in the saved plan yet. */
  extras: Record<string, Course>;
  /** A catalog year chosen in this draft; carried into Build and Save until saved. */
  catalogTerm: TermId | null;
  violations: Violation[];
  announcement: string;
  electiveBaseline: { credits: number; placed: number; valid: boolean } | null;
  /** The draft came from Build plan and replaces the whole plan, so it waits for the user to keep it. */
  fromBuild: boolean;
  setFromBuild: (fromBuild: boolean) => void;
  setElectiveBaseline: (baseline: PlanDraftState["electiveBaseline"]) => void;
  announce: (announcement: string) => void;
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
  announcement: "",
  electiveBaseline: null,
  fromBuild: false,
  setFromBuild: (fromBuild) => set({ fromBuild }),
  setElectiveBaseline: (electiveBaseline) => set({ electiveBaseline }),
  announce: (announcement) => set({ announcement }),
  setChanges: (changes) => set({ changes, violations: [] }),
  setExtras: (extras) => set({ extras }),
  selectCatalogTerm: (catalogTerm) => set({ catalogTerm }),
  setViolations: (violations) => set({ violations }),
  clear: () => set({ changes: {}, extras: {}, catalogTerm: null, violations: [], electiveBaseline: null, fromBuild: false }),
}));
