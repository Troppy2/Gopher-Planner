import { keepPreviousData, useQuery } from "@tanstack/react-query";
import { getCourses } from "@/api/endpoints";
import { queryKeys } from "@/api/queryKeys";
import { usePlanDraft } from "@/features/plan/plan.store";

/** Top course matches for a query, with unsaved plan edits applied to their status. */
export function useCourseSearch(q: string, enabled: boolean, limit = 6) {
  const changes = usePlanDraft((s) => s.changes);
  const { data = [], isFetching } = useQuery({
    queryKey: queryKeys.courses({ q }),
    queryFn: () => getCourses({ q }),
    placeholderData: keepPreviousData,
    enabled,
  });
  const results = data.slice(0, limit).map((c) => (changes[c.code] ? { ...c, ...changes[c.code] } : c));
  return { results, isFetching };
}
