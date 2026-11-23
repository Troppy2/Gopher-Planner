import type { Plan, RequirementStatus } from "@/api/types";
import { Link } from "react-router";
import { CheckCircle2, CircleDashed, AlertCircle, HelpCircle } from "lucide-react";
import { translateWarning } from "@/lib/warnings";

const STATUS_TEXT: Record<RequirementStatus, string> = { satisfied: "met", unsatisfied: "not yet met", needs_review: "needs review" };

/** One scannable status per requirement: done, covered by the plan, or short. */
function chip(completed: RequirementStatus, projected: RequirementStatus) {
  if (completed === "satisfied") return { cls: "met", text: "Met", Icon: CheckCircle2 };
  if (projected === "satisfied") return { cls: "track", text: "On track", Icon: CircleDashed };
  if (projected === "needs_review") return { cls: "review", text: "Needs review", Icon: HelpCircle };
  return { cls: "short", text: "Short", Icon: AlertCircle };
}

/** Completed and projected requirement status, kept separate from credit progress. */
export function RequirementProgressPanel({ plan }: { plan: Plan }) {
  const groups = plan.requirementProgress.filter((item) => item.parentId === null);
  return (
    <section className="card surf" aria-labelledby="req-h">
      <h2 className="h2" id="req-h">
        Degree requirements
      </h2>
      {plan.catalogTerm && <p className="muted req-meta">Catalog year {plan.catalogTerm}. Your advisor and APAS have the final word.</p>}
      {groups.length ? (
        <ul className="req-list">
          {groups.map((group) => {
            const missing = group.projectedStatus === "unsatisfied" ? group.projectedEvidence.missingCodes : [];
            return (
              <li key={group.id} className="req-row">
                <span className="req-name">
                  <b>{group.label}</b>
                  {missing.length > 0 && <span className="muted">Still needed: {missing.join(", ")}</span>}
                </span>
                {(() => {
                  const c = chip(group.completedStatus, group.projectedStatus);
                  return <span className={`req-st ${c.cls}`} title={`Completed: ${STATUS_TEXT[group.completedStatus]}. With your plan: ${STATUS_TEXT[group.projectedStatus]}.`}><c.Icon className="ic sm" aria-hidden />{c.text}</span>;
                })()}
              </li>
            );
          })}
        </ul>
      ) : (
        <p className="muted">
          {plan.catalogTerm === null && plan.availableCatalogTerms.length
            ? <><Link to="/flow-chart">Choose your catalog year</Link> to see your requirements.</>
            : "Requirement details aren't available for your major yet."}
        </p>
      )}
      {plan.warnings.length > 0 && (
        <ul className="warn-list">
          {plan.warnings.map((code) => (
            <li key={code}>{translateWarning(code)}</li>
          ))}
        </ul>
      )}
    </section>
  );
}
