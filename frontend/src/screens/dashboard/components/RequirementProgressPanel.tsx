import type { Plan, RequirementStatus } from "@/api/types";
import { translateWarning } from "@/lib/warnings";

const STATUS_TEXT: Record<RequirementStatus, string> = { satisfied: "met", unsatisfied: "not yet met", needs_review: "needs review" };

/** Completed and projected requirement status, kept separate from credit progress. */
export function RequirementProgressPanel({ plan }: { plan: Plan }) {
  const groups = plan.requirementProgress.filter((item) => item.parentId === null);
  return (
    <section className="card surf" aria-labelledby="req-h">
      <h2 className="h2" id="req-h">
        Degree requirements
      </h2>
      {plan.catalogTerm && <p className="muted">Catalog year {plan.catalogTerm}. Your advisor and APAS have the final word.</p>}
      {groups.length ? (
        <ul className="mlist">
          {groups.map((group) => {
            const missing = group.projectedStatus === "unsatisfied" ? group.projectedEvidence.missingCodes : [];
            return (
              <li key={group.id} className="mrow req-row">
                <span className="mrow-t">
                  <b>{group.label}</b>
                  {missing.length > 0 && <span className="muted">Still needed: {missing.join(", ")}</span>}
                </span>
                <span className="req-status">
                  <span>Completed: {STATUS_TEXT[group.completedStatus]}</span>
                  <span>With your plan: {STATUS_TEXT[group.projectedStatus]}</span>
                </span>
              </li>
            );
          })}
        </ul>
      ) : (
        <p className="muted">
          {plan.catalogTerm === null && plan.availableCatalogTerms.length
            ? "Choose your catalog year in the flow chart to see your requirements."
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
