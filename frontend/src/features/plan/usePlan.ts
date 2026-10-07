import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { getPlan, getProfile, getSummary, savePlan } from "@/api/endpoints";
import { queryKeys } from "@/api/queryKeys";
import type { Course, CourseStatus, Plan, TermId } from "@/api/types";
import { usePlanDraft } from "./plan.store";
import type { DraftEntry } from "./plan.store";
import { buildPlan as buildGreedy } from "./planRules";

export function usePlan() {
  const qc = useQueryClient();
  const planQ = useQuery({ queryKey: queryKeys.plan, queryFn: getPlan });
  const profileQ = useQuery({ queryKey: queryKeys.profile, queryFn: getProfile });
  const summaryQ = useQuery({ queryKey: queryKeys.summary, queryFn: getSummary });
  const { changes, setChanges, clear } = usePlanDraft();

  const saved = planQ.data?.courses ?? [];
  const courses: Course[] = saved.map((c) => (changes[c.code] ? { ...c, ...changes[c.code] } : c));

  /** Turn a full course list back into a minimal draft against the saved plan. */
  const diff = (list: Course[]) => {
    const next: Record<string, DraftEntry> = {};
    for (const c of list) {
      const s = saved.find((x) => x.code === c.code);
      if (s && (s.status !== c.status || s.term !== c.term)) next[c.code] = { status: c.status, term: c.term };
    }
    return next;
  };

  const setCourse = (code: string, status: CourseStatus, term: TermId | null) =>
    setChanges(diff(courses.map((c) => (c.code === code ? { ...c, status, term } : c))));

  // Optimistic: the saved plan updates and the draft clears on click; a failure restores the
  // sent edits underneath anything the user changed since.
  const save = useMutation({
    mutationFn: (sent: Record<string, DraftEntry>) => savePlan(Object.entries(sent).map(([code, e]) => ({ code, ...e }))),
    onMutate: (sent) => {
      const prev = qc.getQueryData<Plan>(queryKeys.plan);
      if (prev) {
        qc.setQueryData<Plan>(queryKeys.plan, {
          ...prev,
          courses: prev.courses.map((c) => (sent[c.code] ? { ...c, ...sent[c.code] } : c)),
        });
      }
      clear();
      return { prev };
    },
    onError: (_e, sent, ctx) => {
      if (ctx?.prev) qc.setQueryData(queryKeys.plan, ctx.prev);
      setChanges({ ...sent, ...usePlanDraft.getState().changes });
    },
    onSuccess: (plan) => qc.setQueryData(queryKeys.plan, plan),
  });

  const goal = summaryQ.data?.creditsTotal ?? 120;

  return {
    plan: planQ.data,
    profile: profileQ.data,
    summary: summaryQ.data,
    isLoading: planQ.isLoading || profileQ.isLoading,
    error: planQ.error ?? profileQ.error,
    refetch: planQ.refetch,
    courses,
    goal,
    pendingCount: Object.keys(changes).length,
    add: (code: string, term: TermId) => setCourse(code, "plan", term),
    remove: (code: string) => setCourse(code, "avail", null),
    build: () => {
      if (planQ.data && profileQ.data) setChanges(diff(buildGreedy(planQ.data, courses, profileQ.data, goal)));
    },
    discard: clear,
    save: () => save.mutate(changes),
    saveState: save,
  };
}
