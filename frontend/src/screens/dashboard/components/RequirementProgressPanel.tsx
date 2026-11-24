import type { Plan, RequirementStatus } from "@/api/types";
import { Button } from "@/ui";
import { useRequirementsParam } from "@/features/requirements/useRequirementsParam";
import { Link } from "react-router";
import { chip } from "@/features/requirements/status";
import { translateWarning } from "@/lib/warnings";

const STATUS_TEXT: Record<RequirementStatus, string> = { satisfied: "met", unsatisfied: "not yet met", needs_review: "needs review" };

/** Completed and projected requirement status, kept separate from credit progress. */
export function RequirementProgressPanel({ plan }: { plan: Plan }) {
  const requirements = useRequirementsParam();
  const groups = plan.requirementProgress.filter((item) => item.parentId === null);
  return (
    <section className="card surf" aria-labelledby="req-h">
      <div className="requirements-panel-header"><h2 className="h2" id="req-h">
        Degree requirements
      </h2><Button variant="ghost" size="sm" onClick={() => requirements.open()}>See all requirements</Button></div>
      {plan.catalogTerm && <p className="muted req-meta">Catalog year {plan.catalogTerm}. Your advisor and APAS have the final word.</p>}
      {groups.length ? (
        <ul className="req-list">
          {groups.map((group) => {
            const missing = group.projectedStatus === "unsatisfied" ? group.projectedEvidence.missingCodes : [];
            return (
              <li key={group.id}><button className="req-row req-open" onClick={() => requirements.open(group.id)}>
                <span className="req-name">
                  <b>{group.label}</b>
                  {missing.length > 0 && <span className="muted">Still needed: {missing.join(", ")}</span>}
                </span>
                {(() => {
                  const c = chip(group.completedStatus, group.projectedStatus);
                  return <span className={`req-st ${c.cls}`} title={`Completed: ${STATUS_TEXT[group.completedStatus]}. With your plan: ${STATUS_TEXT[group.projectedStatus]}.`}><c.Icon className="ic sm" aria-hidden />{c.text}</span>;
                })()}
              </button></li>
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


