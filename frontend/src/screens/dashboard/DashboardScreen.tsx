import { Link, useNavigate } from "react-router";
import { CalendarDays, RefreshCw } from "lucide-react";
import { Button, Callout, EmptyState, SkeletonRows } from "@/ui";
import { usePlan } from "@/features/plan/usePlan";
import { firstFutureIndex } from "@/features/plan/planRules";
import { MetricCard, PercentCard } from "./components/MetricCard";
import { CourseList } from "./components/CourseList";
import { UserDetails } from "./components/UserDetails";
import { RequirementProgressPanel } from "./components/RequirementProgressPanel";
import "./dashboard.css";

export default function DashboardScreen() {
  const navigate = useNavigate();
  const { plan, profile, summary, summaryLoading, summaryError, refetchSummary, courses, isLoading, error, refetch } = usePlan();

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

  const current = courses.filter((c) => c.status === "prog");
  const futureTerms = plan ? plan.terms.slice(firstFutureIndex(plan)) : [];
  const future = futureTerms
    .map((term) => ({ term, list: courses.filter((c) => c.term === term && (c.status === "plan" || c.status === "block")) }))
    .filter((g) => g.list.length);
  const nextTerm = future[0]?.term;
  const build = () => navigate("/flow-chart?build=1");

  return (
    <div className="page" aria-busy={isLoading}>
      <div className="pg-head">
        <div>
          <h1 className="title">Dashboard</h1>
          <p className="sub">{profile ? `Welcome back, ${profile.name || "there"}. ${plan?.currentTerm ?? ""} is in progress.` : " "}</p>
        </div>
        <Button onClick={build}>
          <CalendarDays className="ic" aria-hidden />
          Build my planner
        </Button>
      </div>

      {summaryError ? (
        <div className="dgrid">
          <div className="g12">
            <Callout tone="error" title="We couldn't load your progress.">
              {summaryError.message}{" "}
              <Button size="sm" variant="ghost" onClick={() => refetchSummary()}>
                Try again
              </Button>
            </Callout>
          </div>
        </div>
      ) : summaryLoading || !summary ? (
        <div className="dgrid">
          <div className="g3"><SkeletonRows rows={2} /></div>
          <div className="g4"><SkeletonRows rows={2} /></div>
          <div className="g5"><SkeletonRows rows={2} /></div>
        </div>
      ) : (
        <div className="dgrid">
          <MetricCard className="g3" label="GPA" value={summary.gpa != null ? summary.gpa.toFixed(2) : "N/A"}>
            {summary.gpa != null ? `Out of 4.00, from ${summary.gradedCredits} graded credits` : "No graded credits yet"}
          </MetricCard>
          <MetricCard
            className="g4"
            label="Credits"
            value={summary.creditsCompleted}
            total={summary.creditsTotal}
            bar={{ value: summary.creditsCompleted, max: summary.creditsTotal }}
          >
            {`${Math.max(0, summary.creditsTotal - summary.creditsCompleted)} credits remaining`}
          </MetricCard>
          <PercentCard className="g5" percent={summary.percentComplete} total={summary.creditsTotal} source={summary.source} />
        </div>
      )}

      <div className="dcols">
        <div className="dcol">
            <section className="card surf" aria-labelledby="cur-h">
              <h2 className="h2" id="cur-h">
                Current classes
              </h2>
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
              <h2 className="h2" id="fut-h">
                Future classes
              </h2>
              {isLoading ? (
                <p className="muted">Loading plan…</p>
              ) : future.length ? (
                future.map((g) => (
                  <div key={g.term} className="term-group">
                    <h3 className="term">{g.term}</h3>
                    <CourseList courses={g.list} />
                  </div>
                ))
              ) : (
                <div className="empty-inline">
                  <p className="muted">No planned classes yet.</p>
                  <Button size="sm" onClick={build}>
                    Build my planner
                  </Button>
                </div>
              )}
              {nextTerm && (
                <div className="foot-row">
                  <div>
                    <b>Review your next semester</b>
                    <span className="muted">{nextTerm} is planned.</span>
                  </div>
                  <Link className="btn sm" to={`/flow-chart?term=${encodeURIComponent(nextTerm)}`}>
                    Review {nextTerm}
                  </Link>
                </div>
              )}
            </section>
        </div>
      </div>
    </div>
  );
}
