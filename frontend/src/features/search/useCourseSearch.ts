import { keepPreviousData, useQuery } from "@tanstack/react-query";
import { getCourses } from "@/api/endpoints";
import type { CatalogCourse, Course, CourseStatus } from "@/api/types";
import { queryKeys } from "@/api/queryKeys";
import { usePlanDraft } from "@/features/plan/plan.store";
import { usePlan } from "@/features/plan/usePlan";

export type CourseSearchResult = CatalogCourse & {
  status: CourseStatus;
};

/** Search the catalog and apply saved plan status plus unsaved draft changes. */
export function useCourseSearch(q: string, enabled: boolean, limit = 6) {
  const changes = usePlanDraft((s) => s.changes);
  const { courses: planCourses } = usePlan();

  const { data, isFetching, isError } = useQuery({
    queryKey: queryKeys.courses({ q, limit, offset: 0 }),
    queryFn: () => getCourses({ q, limit, offset: 0 }),
    placeholderData: keepPreviousData,
    enabled,
  });

  const planByCode = new Map<string, Course>(
    planCourses.map((course) => [course.code, course]),
  );

  const results: CourseSearchResult[] = (data?.courses ?? []).map(
    (catalogCourse) => {
      const planCourse = planByCode.get(catalogCourse.code);
      const draftChange = changes[catalogCourse.code];

      return {
        ...catalogCourse,
        status: draftChange?.status ?? planCourse?.status ?? "avail",
      };
    },
  );

  return { results, isFetching, isError };
}
