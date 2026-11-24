import { useRequirementsParam } from "@/features/requirements/useRequirementsParam";
import { useCallback, useEffect, useRef, useState } from "react";
import { useSearchParams } from "react-router";
import { CalendarDays, Maximize, Minus, Network, Plus, RefreshCw } from "lucide-react";
import { Button, Callout, EmptyState, IconButton, SegmentedControl, Select } from "@/ui";
import { usePlan } from "@/features/plan/usePlan";
import { useCourseParam } from "@/features/course-detail/useCourseParam";
import { lastPlanIndex } from "@/features/plan/planRules";
import { useReducedMotion } from "@/hooks/useMediaQuery";
import { ElectiveNote } from "@/features/plan/PlanLabels";
import { SemesterView } from "./components/SemesterView";
import { GraphCanvas } from "./components/GraphCanvas";
import { PlannerSkeleton } from "@/features/loading/ScreenSkeletons";
import type { GraphControls } from "./components/GraphCanvas";
import "./flow-chart.css";


type ViewMode = "sem" | "graph";

export default function FlowChartScreen() {
  const [params, setParams] = useSearchParams();
  const view: ViewMode = params.get("view") === "graph" ? "graph" : "sem";
  const course = useCourseParam();
  const requirements = useRequirementsParam();
  const { plan, profile, courses, goal, isLoading, error, refetch, add, addCourse, editCredits, remove, build, buildState, catalogTerm, selectCatalogTerm, announcement, announce: setLive, pendingCount } = usePlan();
  const [confirmBuild, setConfirmBuild] = useState(false);
  const reduced = useReducedMotion();
  const graph = useRef<GraphControls>(null);
  const buildRequested = useRef(false);

  const setParam = (key: string, value: string | null) => {
    setParams(
      (prev) => {
        const p = new URLSearchParams(prev);
        if (value === null) p.delete(key);
        else p.set(key, value);
        return p;
      },
      { replace: true },
    );
  };

  const focusHeading = (id: string) => {
    requestAnimationFrame(() => {
      const h = document.getElementById(id);
      h?.scrollIntoView({ block: "start", behavior: reduced ? "auto" : "smooth" });
      h?.focus({ preventScroll: true });
    });
  };

  // ?term=Spring 2027 scrolls to that semester card.
  const termParam = params.get("term");
  useEffect(() => {
    if (!plan || !termParam) return;
    const i = plan.terms.indexOf(termParam);
    if (i >= 0) focusHeading(termParam === plan.currentTerm ? "semh-current" : `semh-${i}`);
    setParam("term", null);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [plan, termParam]);

  // ?build=1 asks the server for a dry-run plan and shows it as an unsaved draft.
  const wantsBuild = params.get("build") === "1";
  const needsYear = !!plan && !catalogTerm && plan.availableCatalogTerms.length > 0;
  const runBuild = async () => {
    if (!plan || !profile) return;
    if (needsYear) {
      setLive("Choose your catalog year before building a plan.");
      return;
    }
    try {
      await build();
      setLive(`Planner built through ${plan.terms[lastPlanIndex(plan, profile)]}. Review it, then keep it or discard it.`);
    } catch {
      setLive("The planner could not build a draft. Try again.");
    }
  };
  useEffect(() => {
    if (!wantsBuild) { buildRequested.current = false; return; }
    if (buildRequested.current || !plan || !profile) return;
    buildRequested.current = true;
    setParams(
      (prev) => {
        const p = new URLSearchParams(prev);
        p.delete("build");
        p.delete("view");
        return p;
      },
      { replace: true },
    );
    void runBuild();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [wantsBuild, plan, profile]);

  const openRef = useRef(course.open);
  openRef.current = course.open;
  const onSelect = useCallback((code: string) => openRef.current(code), []);

  if (error) {
    return (
      <div className="page">
        <EmptyState
          title="We couldn't load your plan"
          action={
            <Button onClick={() => refetch()}>
              <RefreshCw className="ic sm" aria-hidden />
              Try again
            </Button>
          }
        >
          Your plan didn't come back. Check your connection and try again.
        </EmptyState>
      </div>
    );
  }

  return (
    <div className={view === "sem" ? "page flow-sem" : "page"}>
      <div className="pg-head flow-head">
        <h1 className="title">My plan</h1>
        <div className="flow-actions">
          <Button variant="ghost" size="sm" onClick={() => requirements.open()}>Requirements</Button>
          {confirmBuild ? <>
            <span className="muted">Replace {pendingCount} unsaved {pendingCount === 1 ? "edit" : "edits"}?</span>
            <Button variant="ghost" size="sm" onClick={() => setConfirmBuild(false)}>Cancel</Button>
            <Button size="sm" onClick={() => { setConfirmBuild(false); void runBuild(); }}>Rebuild</Button>
          </> : <Button size="sm" disabled={!plan || !profile || needsYear || buildState.isPending}
            title={needsYear ? "Pick your catalog year first" : undefined}
            onClick={() => pendingCount > 0 ? setConfirmBuild(true) : void runBuild()}>
            <CalendarDays className="ic sm" aria-hidden />Build plan
          </Button>}
          <SegmentedControl<ViewMode>
          label="View"
          value={view}
          onChange={(v) => setParam("view", v === "graph" ? "graph" : null)}
          options={[
            { value: "sem", label: "Semesters", icon: <CalendarDays className="ic sm" aria-hidden /> },
            { value: "graph", label: "Graph", icon: <Network className="ic sm" aria-hidden /> },
          ]}
          />
        </div>
      </div>

      <p className="vh" role="status" aria-live="polite">
        {announcement}
      </p>
      <ElectiveNote credits={plan?.electiveCredits} />

      {buildState.isPending && (
        <section className="buildcard surf" role="status" aria-labelledby="build-h">
          <h2 className="h2" id="build-h">
            Building your plan…
          </h2>
          <div className="indeterminate" aria-hidden><span /></div>
        </section>
      )}
      {buildState.isError && (
        <Callout tone="error" title="Couldn't build a plan">
          {buildState.error.message}{" "}
          <Button size="sm" variant="ghost" onClick={() => void runBuild()}>Try again</Button>
        </Callout>
      )}
      {needsYear && (
        <Callout tone="info" title="Pick your catalog year to build a plan">
          Use the year on your APAS report.
        </Callout>
      )}
      {plan && view === "sem" && plan.availableCatalogTerms.length > 0 && <div className="semester-catalog-year">
        <Select label="Catalog year" value={catalogTerm ?? ""} onChange={selectCatalogTerm} options={plan.availableCatalogTerms} />
      </div>}

      {isLoading || !plan || !profile ? (
        <PlannerSkeleton view={view} />
      ) : view === "sem" ? (
        <SemesterView
          plan={plan}
          profile={profile}
          courses={courses}
          goal={goal}
          onOpen={course.open}
          onCredits={editCredits}
          onAddCourse={(course, term) => { addCourse(course, term); setLive(`${course.code} added to ${term}.`); }}
          onAdd={(code, i) => {
            add(code, plan.terms[i]);
            setLive(`${code} assigned to ${plan.terms[i]}.`);
          }}
          onRemove={(code, i) => {
            remove(code);
            setLive(`${code} removed from ${plan.terms[i]}.`);
          }}
        />
      ) : (
        <>
          <div className="tb surf">
            {plan.availableCatalogTerms.length > 0 ? (
              <Select
                ariaLabel="Catalog year"
                className="tb-sel"
                value={catalogTerm ?? ""}
                onChange={(term) => selectCatalogTerm(term)}
                options={plan.availableCatalogTerms}
              />
            ) : (
              <span className="muted">{profile.major || "No major selected"}</span>
            )}
            <span className="sp" />
            <div className="zoom">
              <IconButton label="Zoom out" onClick={() => graph.current?.zoomBy(1 / 1.2)}>
                <Minus className="ic" aria-hidden />
              </IconButton>
              <IconButton label="Zoom in" onClick={() => graph.current?.zoomBy(1.2)}>
                <Plus className="ic" aria-hidden />
              </IconButton>
              <IconButton label="Fit plan to screen" onClick={() => graph.current?.fit()}>
                <Maximize className="ic" aria-hidden />
              </IconButton>
              <Button variant="ghost" size="sm" onClick={() => graph.current?.reset()}>
                Reset view
              </Button>
            </div>
          </div>
          <ul className="legend" aria-label="Legend">
            <li>
              <svg viewBox="0 0 16 16" aria-hidden>
                <circle cx="8" cy="8" r="5.5" fill="#1E6B4A" />
              </svg>
              Completed
            </li>
            <li>
              <svg viewBox="0 0 16 16" aria-hidden>
                <circle cx="8" cy="8" r="5.5" fill="#FFCC33" stroke="#8A5F00" strokeWidth="2" />
              </svg>
              In progress
            </li>
            <li>
              <svg viewBox="0 0 16 16" aria-hidden>
                <circle cx="8" cy="8" r="5.5" fill="#FBF8F2" stroke="#7A0019" strokeWidth="2" />
              </svg>
              Planned
            </li>
            <li>
              <svg viewBox="0 0 16 16" aria-hidden>
                <circle cx="8" cy="8" r="5" fill="none" stroke="var(--muted)" strokeWidth="1.5" />
              </svg>
              Available
            </li>
            <li>
              <svg viewBox="0 0 16 16" aria-hidden>
                <path d="M8 1.5L14.5 8L8 14.5L1.5 8z" fill="none" stroke="var(--muted)" strokeWidth="1.5" strokeDasharray="2 2" />
              </svg>
              Locked
            </li>
          </ul>
          <GraphCanvas ref={graph} courses={courses} terms={plan.terms} selected={course.code} onSelect={onSelect} reducedMotion={reduced} />
          <p className="hint graph-hint">Ctrl/Cmd + scroll to zoom. Drag a course to pin it.</p>
        </>
      )}
    </div>
  );
}

