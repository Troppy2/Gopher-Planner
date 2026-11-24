import type { Plan, RequirementStatus } from "@/api/types";
import { Button } from "@/ui";
import { useRequirementsParam } from "@/features/requirements/useRequirementsParam";
import { Link } from "react-router";
import { ChevronRight } from "lucide-react";
import { chip } from "@/features/requirements/status";
import { PlanWarnings } from "@/features/plan/PlanWarnings";

const STATUS_TEXT: Record<RequirementStatus, string> = { satisfied: "met", unsatisfied: "not yet met", needs_review: "needs review" };

/** Completed and projected requirement status, kept separate from credit progress. */
export function RequirementProgressPanel({ plan }: { plan: Plan }) {
  const requirements = useRequirementsParam();
  const groups = plan.requirementProgress.filter((item) => item.parentId === null);
  return (
    <section className="card surf" aria-labelledby="req-h">
      <div className="dashboard-section-heading">
        <h2 className="h2" id="req-h">
          Degree requirements
        </h2>
        <Button variant="ghost" size="sm" onClick={() => requirements.open()} aria-label="See all requirements">
          See all
        </Button>
      </div>
      {plan.catalogTerm && <p className="muted req-meta">Catalog year {plan.catalogTerm}. Your advisor and APAS have the final word.</p>}
      {groups.length ? (
        <ul className="req-list">
          {groups.map((group) => {
            const missing = group.projectedStatus === "unsatisfied" ? group.projectedEvidence.missingCodes : [];
            return (
              <li key={group.id}>
                <button type="button" className="req-row req-open hover-row" onClick={() => requirements.open(group.id)}>
                <span className="req-name">
                  <b>{group.label}</b>
                  {missing.length > 0 && <span className="muted">Still needed: {missing.join(", ")}</span>}
                </span>
                {(() => {
                  const c = chip(group.completedStatus, group.projectedStatus);
                  return (
                    <span className={`req-st ${c.cls}`} title={`Completed: ${STATUS_TEXT[group.completedStatus]}. With your plan: ${STATUS_TEXT[group.projectedStatus]}.`}>
                      <c.Icon className="ic sm" aria-hidden />
                      {c.text}
                      <ChevronRight className="ic sm req-chevron" aria-hidden />
                    </span>
                  );
                })()}
                </button>
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
      <PlanWarnings warnings={plan.warnings} />
    </section>
  );
}


