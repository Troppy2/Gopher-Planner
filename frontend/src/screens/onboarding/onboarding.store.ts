import { create } from "zustand";

export type ImportMethod = "upload" | "manual" | "skip";

export interface UploadState {
  fileName: string;
  sizeLabel: string;
  /** Set once the server accepted the file; parsing finishes inside that request. */
  transcriptId: string | null;
}

export interface ManualCourse {
  code: string;
  title: string;
  /** From the catalog result, so saved coursework never guesses credits. */
  credits: number;
  status: "done" | "prog";
}

export interface ProfileDraft {
  name: string;
  standing: string;
  major: string;
  careerGoals: string;
  creditLoad: string;
  graduationTarget: string;
}

/** A draft cache that survives Back between steps. The server's saved coursework is the source of truth. */
interface OnboardingState {
  method: ImportMethod;
  upload: UploadState | null;
  manual: ManualCourse[];
  profile: ProfileDraft | null;
  setMethod: (m: ImportMethod) => void;
  setUpload: (u: UploadState | null) => void;
  addManual: (c: ManualCourse) => void;
  setManual: (list: ManualCourse[]) => void;
  setManualStatus: (code: string, status: ManualCourse["status"]) => void;
  removeManual: (code: string) => void;
  setProfile: (p: ProfileDraft) => void;
  reset: () => void;
}

const initial = { method: "upload" as ImportMethod, upload: null, manual: [], profile: null };

export const useOnboarding = create<OnboardingState>((set) => ({
  ...initial,
  setMethod: (method) => set({ method }),
  setUpload: (upload) => set({ upload }),
  addManual: (c) => set((s) => (s.manual.some((m) => m.code === c.code) ? s : { manual: [...s.manual, c] })),
  setManual: (manual) => set({ manual }),
  setManualStatus: (code, status) => set((s) => ({ manual: s.manual.map((m) => (m.code === code ? { ...m, status } : m)) })),
  removeManual: (code) => set((s) => ({ manual: s.manual.filter((m) => m.code !== code) })),
  setProfile: (profile) => set({ profile }),
  reset: () => set(initial),
}));
