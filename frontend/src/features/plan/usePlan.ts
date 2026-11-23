import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { generatePlan, getPlan, getProfile, getSummary, savePlan } from "@/api/endpoints";
import { ApiError } from "@/api/client";
import { queryKeys } from "@/api/queryKeys";
import type { Course, CourseStatus, Plan, TermId } from "@/api/types";
import { usePlanDraft } from "./plan.store";
import type { DraftEntry } from "./plan.store";
import { sumCredits } from "./planRules";

export function usePlan() {
  const qc = useQueryClient();
  const planQ = useQuery({ queryKey: queryKeys.plan, queryFn: getPlan });
  const profileQ = useQuery({ queryKey: queryKeys.profile, queryFn: getProfile });
  const summaryQ = useQuery({ queryKey: queryKeys.summary, queryFn: getSummary });
  const { changes, extras, catalogTerm: draftTerm, violations, announcement, announce, electiveBaseline, setElectiveBaseline, fromBuild, setFromBuild, setChanges, setExtras, selectCatalogTerm, setViolations, clear } = usePlanDraft();

  const saved = planQ.data?.courses ?? [];
  const known = new Set(saved.map((c) => c.code));
  const courses: Course[] = [
    ...saved.map((c) => {
      const merged = changes[c.code] ? extras[c.code] ?? c : c;
      return changes[c.code] ? { ...merged, ...changes[c.code] } : merged;
    }),
    ...Object.values(extras).filter((c) => !known.has(c.code)).map((c) => (changes[c.code] ? { ...c, ...changes[c.code] } : c)),
  ];
  /** The catalog year Build and Save use: a draft selection, else the saved one. */
  const catalogTerm = draftTerm ?? planQ.data?.catalogTerm ?? null;

  /** Turn a full course list back into a minimal draft against the saved plan. */
  const diff = (list: Course[]) => {
    const next: Record<string, DraftEntry> = {};
    for (const c of list) {
      const s = saved.find((x) => x.code === c.code);
      if ((s && (s.status !== c.status || s.term !== c.term || s.slot !== c.slot || s.credits !== c.credits)) || (!s && (c.status === "plan" || c.status === "prog"))) next[c.code] = {
        status: c.status, term: c.term, ...(c.slot && c.status === "plan" ? { slot: c.slot } : {}),
        ...(c.status === "prog" ? { credits: c.credits } : {}),
      };
    }
    return next;
  };

  const setCourse = (code: string, status: CourseStatus, term: TermId | null) =>
    setChanges(diff(courses.map((c) => (c.code === code ? { ...c, status, term } : c))));

  // Optimistic: the saved plan updates and the draft clears on click; a failure restores the
  // sent edits underneath anything the user changed since, and keeps the violations.
  const save = useMutation({
    mutationFn: ({ sent, term }: { sent: Record<string, DraftEntry>; extras: Record<string, Course>; term: TermId | null; balance: typeof electiveBaseline }) =>
      savePlan(Object.entries(sent).map(([code, e]) => ({ code, ...e })), term),
    onMutate: ({ sent, extras: sentExtras }) => {
      const prev = qc.getQueryData<Plan>(queryKeys.plan);
      if (prev) {
        qc.setQueryData<Plan>(queryKeys.plan, {
          ...prev,
          courses: [
            ...prev.courses,
            ...Object.values(sentExtras).filter(c => !prev.courses.some(saved => saved.code === c.code) && sent[c.code]),
          ].map(c => sent[c.code] ? { ...(sentExtras[c.code] ?? c), ...sent[c.code] } : c),
        });
      }
      return { prev };
    },
    onError: (error, vars, ctx) => {
      if (ctx?.prev) qc.setQueryData(queryKeys.plan, ctx.prev);
      const state = usePlanDraft.getState();
      setExtras({ ...vars.extras, ...state.extras });
      setElectiveBaseline(state.electiveBaseline ?? vars.balance);
      setChanges({ ...vars.sent, ...state.changes });
      selectCatalogTerm(vars.term);
      setViolations(error instanceof ApiError ? error.violations : []);
    },
    onSuccess: async (plan) => {
      qc.setQueryData(queryKeys.plan, plan);
      await Promise.all([
        qc.invalidateQueries({ queryKey: queryKeys.summary }),
        qc.invalidateQueries({ queryKey: queryKeys.coursework }),
      ]);
    },
  });

  const build = useMutation({
    mutationFn: () => generatePlan({ dryRun: true, catalogTerm }),
    onSuccess: (result) => {
      // A dry run is an unsaved draft: compare it with the saved plan instead of replacing it.
      const draftExtras: Record<string, Course> = {};
      for (const c of result.plan.courses) draftExtras[c.code] = c;
      setExtras(draftExtras);
      setElectiveBaseline({ credits: result.plan.electiveCredits ?? 0, placed: sumCredits(result.plan.courses.filter(c => c.status === "plan" || c.status === "prog")), valid: !!result.plan.catalogTerm });
      const generated = new Set(result.plan.courses.map(c => c.code));
      const removed = saved.filter(c => c.status === "plan" && !generated.has(c.code)).map(c => ({ ...c, status: "avail" as const, term: null, slot: null }));
      setChanges(diff([...result.plan.courses, ...removed]));
      if (result.plan.catalogTerm) selectCatalogTerm(result.plan.catalogTerm);
      setFromBuild(true);
    },
  });

  const goal = summaryQ.data?.creditsTotal ?? 120;
  const balance = electiveBaseline ?? (planQ.data?.electiveCredits !== undefined ? {
    credits: planQ.data.electiveCredits, placed: sumCredits(saved.filter(c => c.status === "plan" || c.status === "prog")), valid: !!planQ.data.catalogTerm,
  } : null);
  const electiveCredits = balance?.valid ? Math.max(0, balance.credits + balance.placed - sumCredits(courses.filter(c => c.status === "plan" || c.status === "prog"))) : 0;

  return {
    announcement,
    announce,
    plan: planQ.data ? { ...planQ.data, electiveCredits } : undefined,
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
    /** True while the pending edits are a generated plan the user hasn't kept yet. */
    isBuildDraft: fromBuild,
    /** Fingerprint of the pending edits, for autosave. */
    draftKey: JSON.stringify([changes, draftTerm]),
    /** A catalog year chosen in the draft but not saved yet. */
    versionPending: !!draftTerm && draftTerm !== planQ.data?.catalogTerm,
    add: (code: string, term: TermId) => setCourse(code, term === planQ.data?.currentTerm ? "prog" : "plan", term),
    editCredits: (code: string, credits: number) => setChanges(diff(courses.map(c => c.code === code ? { ...c, credits } : c))),
    /** Add a course that may not be in the saved plan, such as a catalog search result. */
    addCourse: (course: Course, term: TermId) => {
      if (!known.has(course.code)) setExtras({ ...usePlanDraft.getState().extras, [course.code]: course });
      const status = term === planQ.data?.currentTerm ? "prog" : "plan";
      setChanges({ ...diff(courses), [course.code]: { status, term, ...(status === "prog" ? { credits: course.credits } : {}) } });
    },
    remove: (code: string) => setCourse(code, "avail", null),
    swap: (code: string, replacement: Course) => {
      const old = courses.find(c => c.code === code);
      if (!old?.term || !old.slot) return;
      const next = { ...replacement, slot: old.slot, slotCategories: old.slotCategories, status: "plan" as const, term: old.term };
      setExtras({ ...usePlanDraft.getState().extras, [next.code]: next });
      setChanges(diff([...courses.filter(c => c.code !== next.code).map(c => c.code === code ? { ...c, status: "avail" as const, term: null } : c), next]));
    },
    build: () => build.mutateAsync(),
    buildState: build,
    discard: clear,
    save: () => {
      const sent = usePlanDraft.getState().changes;
      const sentExtras = usePlanDraft.getState().extras;
      const balance = usePlanDraft.getState().electiveBaseline;
      clear();
      return save.mutateAsync({ sent, extras: sentExtras, term: catalogTerm, balance }).catch(() => undefined);
    },
    saveState: save,
  };
}
