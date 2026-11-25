import { useState } from "react";
import { Link, useNavigate } from "react-router";
import { CalendarDays, RefreshCw } from "lucide-react";
import { Button, Callout, EmptyState } from "@/ui";
import { DashboardSkeleton, MetricsSkeleton } from "@/features/loading/ScreenSkeletons";
import { usePlan } from "@/features/plan/usePlan";
import { firstFutureIndex, sumCredits } from "@/features/plan/planRules";
import { MetricCard, PercentCard } from "./components/MetricCard";
import { CourseList } from "./components/CourseList";
import { UserDetails } from "./components/UserDetails";
import { RequirementProgressPanel } from "./components/RequirementProgressPanel";
import { LiberalEdPanel } from "./components/LiberalEdPanel";
import "./dashboard.css";

export default function DashboardScreen() {
  const navigate = useNavigate();
  const [allTerms, setAllTerms] = useState(false);
  const { plan, profile, summary, summaryLoading, summaryError, refetchSummary, courses, isLoading, error, refetch, addCourse } = usePlan();

  if (error) {
    return (
      <div className="page">
        <EmptyState
          title="We couldn't load your dashboard"
          action={
            <Button onClick={() => refetch()}>
              <RefreshCw className="ic sm" aria-hidden />
              Try again
            </Button>
          }
        >
          Your plan data didn't come back. Check your connection and try again.
        </EmptyState>
      </div>
    );
  }

  if (isLoading) return <DashboardSkeleton />;

  const current = courses.filter((c) => (c.status === "prog" || c.status === "plan") && c.term === plan?.currentTerm);
  const futureTerms = plan ? plan.terms.slice(firstFutureIndex(plan)) : [];
  const future = futureTerms
    .map((term) => ({ term, list: courses.filter((c) => c.term === term && (c.status === "plan" || c.status === "prog" || c.status === "block")) }))
    .filter((g) => g.list.length);
  const nextTerm = future[0]?.term;
  const hasPlan = courses.some((c) => c.status === "plan" || c.status === "block");
  const openPlan = () => navigate(hasPlan ? "/flow-chart" : "/flow-chart?build=1");

  return (
    <div className="page" aria-busy={isLoading}>
      <div className="pg-head">
        <div>
          <h1 className="title">Dashboard</h1>
          <p className="sub">{profile ? `Welcome back, ${profile.name || "there"}. ${plan?.currentTerm ?? ""} is in progress.` : " "}</p>
        </div>
        <Button onClick={openPlan}>
          <CalendarDays className="ic" aria-hidden />
          {hasPlan ? "Open my plan" : "Build my plan"}
        </Button>
      </div>

      {summaryError ? (
        <div className="dgrid">
          <div className="g12">
            <Callout tone="error" title="Couldn't load your progress">
              {summaryError.message}{" "}
              <Button size="sm" variant="ghost" onClick={() => refetchSummary()}>
                Try again
              </Button>
            </Callout>
          </div>
        </div>
      ) : summaryLoading || !summary ? (
        <MetricsSkeleton />
      ) : (
        <div className="dgrid">
          <MetricCard className="g3" label="GPA" value={summary.gpa != null ? summary.gpa.toFixed(2) : "N/A"}>
            {summary.gpa != null ? `Out of 4.00, from ${summary.gradedCredits} graded credits` : "No graded credits yet"}
          </MetricCard>
          <MetricCard
            className="g4"
            label="Completed credits"
            value={summary.creditsCompleted}
            total={summary.creditsTotal}
            bar={{ value: summary.creditsCompleted, max: summary.creditsTotal }}
          >
            {`${Math.max(0, summary.creditsTotal - summary.creditsCompleted)} credits remaining`}
            {!isLoading && <span className="dashboard-credit-breakdown">{sumCredits(courses.filter(c => c.status === "prog"))} in progress · {sumCredits(courses.filter(c => c.status === "plan"))} planned</span>}
            {!!plan?.electiveCredits && plan.electiveCredits > 0 && (
              <span className="dashboard-credit-breakdown">{plan.electiveCredits} more credits of free electives to plan</span>
            )}
          </MetricCard>
          <PercentCard className="g5" percent={summary.percentComplete} total={summary.creditsTotal} source={summary.source} />
        </div>
      )}

      <div className="dcols">
        <div className="dcol">
            <section className="card surf" aria-labelledby="cur-h">
              <div className="dashboard-section-heading">
              <h2 className="h2" id="cur-h">
                Current classes
              </h2>
              <Link className="btn ghost sm" to={`/flow-chart?term=${encodeURIComponent(plan?.currentTerm ?? "")}`}>Edit semester</Link>
              </div>
              {isLoading ? <p className="muted">Loading classes…</p> : current.length ? <CourseList courses={current} /> : <p className="muted">No classes in progress this term.</p>}
            </section>
            {plan && <RequirementProgressPanel plan={plan} />}
            <section className="card surf d-details" aria-labelledby="det-h">
              <h2 className="h2" id="det-h">
                User details
              </h2>
              <UserDetails profile={profile} />
            </section>
        </div>
        <div className="dcol">
            <section className="card surf" aria-labelledby="fut-h">
              <div className="dashboard-section-heading">
                <h2 className="h2" id="fut-h">
                  Future classes
                </h2>
                {nextTerm && <Link className="btn ghost sm" to={`/flow-chart?term=${encodeURIComponent(nextTerm)}`}>Plan {nextTerm}</Link>}
              </div>
              {isLoading ? (
                <p className="muted">Loading plan…</p>
              ) : future.length ? (
                <>
                  {(allTerms ? future : future.slice(0, 2)).map((g) => (
                    <div key={g.term} className="term-group">
                      <h3 className="term">{g.term}</h3>
                      <CourseList courses={g.list} future />
                    </div>
                  ))}
                  {future.length > 2 && (
                    <Button variant="ghost" size="sm" className="show-more" aria-expanded={allTerms} onClick={() => setAllTerms(!allTerms)}>
                      {allTerms ? "Show fewer terms" : `Show ${future.length - 2} more terms`}
                    </Button>
                  )}
                </>
              ) : (
                <div className="empty-inline">
                  <p className="muted">No planned classes yet.</p>
                  <Button size="sm" onClick={openPlan}>
                    Build my plan
                  </Button>
                </div>
              )}
            </section>
            {plan && (
              <LiberalEdPanel
                plan={plan}
                profile={profile}
                courses={courses}
                onAdd={addCourse}
              />
            )}
        </div>
      </div>
    </div>
  );
}
