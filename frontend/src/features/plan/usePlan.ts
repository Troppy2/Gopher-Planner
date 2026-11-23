import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { generatePlan, getPlan, getProfile, getSummary, savePlan } from "@/api/endpoints";
import { ApiError } from "@/api/client";
import { queryKeys } from "@/api/queryKeys";
import type { Course, CourseStatus, Plan, TermId } from "@/api/types";
import { usePlanDraft } from "./plan.store";
import type { DraftEntry } from "./plan.store";

export function usePlan() {
  const qc = useQueryClient();
  const planQ = useQuery({ queryKey: queryKeys.plan, queryFn: getPlan });
  const profileQ = useQuery({ queryKey: queryKeys.profile, queryFn: getProfile });
  const summaryQ = useQuery({ queryKey: queryKeys.summary, queryFn: getSummary });
  const { changes, extras, catalogTerm: draftTerm, violations, setChanges, setExtras, selectCatalogTerm, setViolations, clear } = usePlanDraft();

  const saved = planQ.data?.courses ?? [];
  const known = new Set(saved.map((c) => c.code));
  const courses: Course[] = [
    ...saved.map((c) => (changes[c.code] ? { ...c, ...changes[c.code] } : c)),
    ...Object.values(extras).filter((c) => !known.has(c.code)).map((c) => (changes[c.code] ? { ...c, ...changes[c.code] } : c)),
  ];
  /** The catalog year Build and Save use: a draft selection, else the saved one. */
  const catalogTerm = draftTerm ?? planQ.data?.catalogTerm ?? null;

  /** Turn a full course list back into a minimal draft against the saved plan. */
  const diff = (list: Course[]) => {
    const next: Record<string, DraftEntry> = {};
    for (const c of list) {
      const s = saved.find((x) => x.code === c.code);
      if ((s && (s.status !== c.status || s.term !== c.term)) || (!s && c.status === "plan")) next[c.code] = { status: c.status, term: c.term };
    }
    return next;
  };

  const setCourse = (code: string, status: CourseStatus, term: TermId | null) =>
    setChanges(diff(courses.map((c) => (c.code === code ? { ...c, status, term } : c))));

  // Optimistic: the saved plan updates and the draft clears on click; a failure restores the
  // sent edits underneath anything the user changed since, and keeps the violations.
  const save = useMutation({
    mutationFn: ({ sent, term }: { sent: Record<string, DraftEntry>; extras: Record<string, Course>; term: TermId | null }) =>
      savePlan(Object.entries(sent).map(([code, e]) => ({ code, ...e })), term),
    onMutate: ({ sent }) => {
      const prev = qc.getQueryData<Plan>(queryKeys.plan);
      if (prev) {
        qc.setQueryData<Plan>(queryKeys.plan, {
          ...prev,
          courses: prev.courses.map((c) => (sent[c.code] ? { ...c, ...sent[c.code] } : c)),
        });
      }
      return { prev };
    },
    onError: (error, vars, ctx) => {
      if (ctx?.prev) qc.setQueryData(queryKeys.plan, ctx.prev);
      const state = usePlanDraft.getState();
      setExtras({ ...vars.extras, ...state.extras });
      setChanges({ ...vars.sent, ...state.changes });
      selectCatalogTerm(vars.term);
      setViolations(error instanceof ApiError ? error.violations : []);
    },
    onSuccess: (plan) => qc.setQueryData(queryKeys.plan, plan),
  });

  const build = useMutation({
    mutationFn: () => generatePlan({ dryRun: true, catalogTerm }),
    onSuccess: (result) => {
      // A dry run is an unsaved draft: compare it with the saved plan instead of replacing it.
      const draftExtras: Record<string, Course> = {};
      for (const c of result.plan.courses) if (!known.has(c.code)) draftExtras[c.code] = c;
      setExtras(draftExtras);
      setChanges(diff(result.plan.courses));
      if (result.plan.catalogTerm) selectCatalogTerm(result.plan.catalogTerm);
    },
  });

  const goal = summaryQ.data?.creditsTotal ?? 120;

  return {
    plan: planQ.data,
    profile: profileQ.data,
    summary: summaryQ.data,
    summaryLoading: summaryQ.isLoading,
    summaryError: summaryQ.error,
    refetchSummary: summaryQ.refetch,
    isLoading: planQ.isLoading || profileQ.isLoading,
    error: planQ.error ?? profileQ.error,
    refetch: planQ.refetch,
    courses,
    goal,
    catalogTerm,
    selectCatalogTerm,
    violations,
    pendingCount: Object.keys(changes).length,
    /** A catalog year chosen in the draft but not saved yet. */
    versionPending: !!draftTerm && draftTerm !== planQ.data?.catalogTerm,
    add: (code: string, term: TermId) => setCourse(code, "plan", term),
    /** Add a course that may not be in the saved plan, such as a catalog search result. */
    addCourse: (course: Course, term: TermId) => {
      if (!known.has(course.code)) setExtras({ ...usePlanDraft.getState().extras, [course.code]: course });
      setChanges({ ...diff(courses), [course.code]: { status: "plan", term } });
    },
    remove: (code: string) => setCourse(code, "avail", null),
    build: () => build.mutateAsync(),
    buildState: build,
    discard: clear,
    save: () => {
      const sent = usePlanDraft.getState().changes;
      const sentExtras = usePlanDraft.getState().extras;
      clear();
      return save.mutateAsync({ sent, extras: sentExtras, term: catalogTerm }).catch(() => undefined);
    },
    saveState: save,
  };
}
