import type { CourseFilters } from "./types";

export const queryKeys = {
  summary: ["summary"] as const,
  profile: ["profile"] as const,
  options: ["options"] as const,
  plan: ["plan"] as const,
  courses: (f: CourseFilters) => ["courses", f] as const,
  course: (code: string) => ["course", code] as const,
  transcript: (id: string) => ["transcript", id] as const,
};
