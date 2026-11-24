import type { CourseFilters } from "./types";

export const queryKeys = {
  reports: ["reports"] as const,
  summary: ["summary"] as const,
  profile: ["profile"] as const,
  options: ["options"] as const,
  plan: ["plan"] as const,
  coursework: ["coursework"] as const,
  programs: ["programs"] as const,
  courses: (f: CourseFilters) => ["courses", f] as const,
  course: (code: string) => ["course", code] as const,
  transcript: (id: string) => ["transcript", id] as const,
};
