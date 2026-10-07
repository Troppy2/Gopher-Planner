import { create } from "zustand";
import type { CourseStatus, TermId } from "@/api/types";

export interface DraftEntry {
  status: CourseStatus;
  term: TermId | null;
}

/** Only the edits made since the last save. Saved plan + draft = what the user sees. */
interface PlanDraftState {
  changes: Record<string, DraftEntry>;
  setChanges: (changes: Record<string, DraftEntry>) => void;
  clear: () => void;
}

export const usePlanDraft = create<PlanDraftState>((set) => ({
  changes: {},
  setChanges: (changes) => set({ changes }),
  clear: () => set({ changes: {} }),
}));
