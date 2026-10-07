import { useCallback, useEffect, useRef, useState } from "react";
import { useSearchParams } from "react-router";
import { CalendarDays, Maximize, Minus, Network, Plus, RefreshCw } from "lucide-react";
import { Button, EmptyState, IconButton, ProgressBar, SegmentedControl, Select, StepList } from "@/ui";
import { usePlan } from "@/features/plan/usePlan";
import { useCourseParam } from "@/features/course-detail/useCourseParam";
import { firstFutureIndex, lastPlanIndex, projectedCredits } from "@/features/plan/planRules";
import { useReducedMotion } from "@/hooks/useMediaQuery";
import { SemesterView } from "./components/SemesterView";
import { GraphCanvas } from "./components/GraphCanvas";
import type { GraphControls } from "./components/GraphCanvas";
import "./flow-chart.css";

const BUILD_STEPS = [
  "Reading your progress",
  "Checking prerequisites and when courses are offered",
  "Filling each semester to your credit load",
  "Checking your graduation total",
];

type ViewMode = "sem" | "graph";

export default function FlowChartScreen() {
  const [params, setParams] = useSearchParams();
  const view: ViewMode = params.get("view") === "graph" ? "graph" : "sem";
  const course = useCourseParam();
  const { plan, profile, courses, goal, isLoading, error, refetch, add, remove, build } = usePlan();
  const reduced = useReducedMotion();
  const graph = useRef<GraphControls>(null);
  const [live, setLive] = useState("");
  const [buildStep, setBuildStep] = useState<number | null>(null);
  const [major, setMajor] = useState("");

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
    if (i >= 0) focusHeading(`semh-${i}`);
    setParam("term", null);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [plan, termParam]);

  // ?build=1 runs the planner, then shows the result as an unsaved draft.
  const wantsBuild = params.get("build") === "1";
  const buildTimers = useRef<number[]>([]);
  useEffect(() => () => buildTimers.current.forEach(clearTimeout), []);
  useEffect(() => {
    if (!wantsBuild || !plan || !profile) return;
    setParams(
      (prev) => {
        const p = new URLSearchParams(prev);
        p.delete("build");
        p.delete("view");
        return p;
      },
      { replace: true },
    );
    setBuildStep(0);
    const gap = reduced ? 120 : 550;
    buildTimers.current = BUILD_STEPS.map((_, i) => window.setTimeout(() => setBuildStep(i + 1), gap * (i + 1)));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [wantsBuild, plan, profile]);

  useEffect(() => {
    if (buildStep !== BUILD_STEPS.length || !plan || !profile) return;
    build();
    setBuildStep(null);
    const last = lastPlanIndex(plan, profile);
    setLive(`Planner built through ${plan.terms[last]}. Review the semesters, then save or discard.`);
    focusHeading(`semh-${firstFutureIndex(plan)}`);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [buildStep]);

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
        <h1 className="title">Flow chart</h1>
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

      <p className="vh" role="status" aria-live="polite">
        {live}
      </p>

      {buildStep !== null && (
        <section className="buildcard surf" role="status" aria-labelledby="build-h">
          <h2 className="h2" id="build-h">
            Building your planner
          </h2>
          <ProgressBar label="Planner progress" value={buildStep} max={BUILD_STEPS.length} />
          <StepList steps={BUILD_STEPS} done={buildStep} />
        </section>
      )}

      {isLoading || !plan || !profile ? (
        <div className="sem">
          {[0, 1, 2].map((i) => (
            <div key={i} className="semcard surf sem-skel" aria-hidden />
          ))}
        </div>
      ) : view === "sem" ? (
        <SemesterView
          plan={plan}
          profile={profile}
          courses={courses}
          goal={goal}
          onOpen={course.open}
          onAdd={(code, i) => {
            add(code, plan.terms[i]);
            setLive(`${code} added to ${plan.terms[i]}. ${projectedCredits(plan.baseCredits, courses) + (courses.find((c) => c.code === code)?.credits ?? 0)} credits projected.`);
          }}
          onRemove={(code, i) => {
            remove(code);
            setLive(`${code} removed from ${plan.terms[i]}.`);
          }}
        />
      ) : (
        <>
          <div className="tb surf">
            <Select
              ariaLabel="Major"
              className="tb-sel"
              value={major || profile.major}
              onChange={setMajor}
              options={[profile.major, ...["Computer Science B.S.", "Data Science B.S."].filter((m) => m !== profile.major)]}
            />
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
                <circle cx="8" cy="8" r="5" fill="none" stroke="#625A5C" strokeWidth="1.5" />
              </svg>
              Available
            </li>
            <li>
              <svg viewBox="0 0 16 16" aria-hidden>
                <path d="M8 1.5L14.5 8L8 14.5L1.5 8z" fill="#F6E6CC" stroke="#A86400" strokeWidth="1.8" />
              </svg>
              Locked
            </li>
          </ul>
          <GraphCanvas ref={graph} courses={courses} terms={plan.terms} selected={course.code} onSelect={onSelect} reducedMotion={reduced} />
          <p className="hint graph-hint">Drag a course to pin it. Scroll or pinch to zoom. Double-click the background to fit.</p>
        </>
      )}
    </div>
  );
}
