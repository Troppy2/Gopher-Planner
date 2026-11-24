import { useEffect, useRef, useState } from "react";
import { Link } from "react-router";
import type { Plan, RequirementProgress } from "@/api/types";
import { Button, Callout, Modal } from "@/ui";
import { usePlan } from "@/features/plan/usePlan";
import { ReportProblemButton } from "@/features/reports/ReportProblemButton";
import { chip } from "@/screens/dashboard/components/RequirementProgressPanel";
import { useRequirementsParam } from "./useRequirementsParam";
import "./requirements.css";

/** Reporting entry point while the fuller requirements-modal slice is pending. */
export function RequirementsModal() {
  const { groupId, close } = useRequirementsParam();
  const { plan, isLoading, error, refetch } = usePlan();
  if (!groupId) return null;
  return <Modal open onOpenChange={open => !open && close()} title="Degree requirements" size="lg"
    subtitle={plan?.catalogTerm ? `Catalog year ${plan.catalogTerm}. Your advisor and APAS have the final word.` : undefined}>
    {isLoading ? <p role="status">Loading requirements...</p> : error
      ? <Callout tone="error" title="Couldn't load requirements"><Button onClick={() => void refetch()}>Try again</Button></Callout>
      : plan && <RequirementGroups key={groupId} plan={plan} focused={groupId} />}
  </Modal>;
}

export function RequirementGroups({ plan, focused }: { plan: Plan; focused: string }) {
  const groups = plan.requirementProgress.filter(n => n.parentId === null);
  if (!groups.length) return <p className="muted">{!plan.catalogTerm && plan.availableCatalogTerms.length
    ? <><Link to="/flow-chart">Choose your catalog year</Link> to see your requirements.</>
    : "Requirement details aren't available for your major yet."}</p>;
  return <div className="requirement-groups">{groups.map(group =>
    <RequirementGroup key={group.id} group={group} plan={plan} focused={focused === group.id} />)}</div>;
}

function RequirementGroup({ group, plan, focused }: { group: RequirementProgress; plan: Plan; focused: boolean }) {
  const status = chip(group.completedStatus, group.projectedStatus);
  const [expanded, setExpanded] = useState(focused || status.cls === "short" || status.cls === "review");
  const header = useRef<HTMLButtonElement>(null);
  useEffect(() => {
    if (focused) {
      header.current?.focus();
      header.current?.scrollIntoView?.({ block: "nearest" });
    }
  }, [focused]);
  const descendants: RequirementProgress[] = [];
  const collect = (parent: string) => {
    for (const node of plan.requirementProgress.filter(n => n.parentId === parent)) {
      descendants.push(node);
      collect(node.id);
    }
  };
  collect(group.id);
  return <section className="requirement-group">
    <div className="requirement-group-header">
      <button ref={header} className="requirement-toggle" aria-expanded={expanded} aria-controls={`report-group-${group.id}`} onClick={() => setExpanded(!expanded)}>
        <b>{group.label}</b><span className="muted">{group.category}</span>
        <span className={`req-st ${status.cls}`}><status.Icon className="ic sm" aria-hidden />{status.text}</span>
      </button>
      <ReportProblemButton target={{ type: "requirement", requirementId: group.id, label: group.label }} />
    </div>
    {expanded && <div id={`report-group-${group.id}`} className="requirement-group-body">
      {descendants.map(node => <div key={node.id}>
        <p><b>{node.label}</b></p>
        {node.projectedEvidence.minCourses !== undefined && <p>{node.projectedEvidence.matchedCourses ?? 0} of {node.projectedEvidence.minCourses} courses chosen</p>}
        {node.projectedEvidence.requiredCredits !== undefined && <p>{node.projectedEvidence.matchedCredits ?? 0} of {node.projectedEvidence.requiredCredits} credits</p>}
        {node.details.map((text, i) => <p className="muted" key={i}>{text}</p>)}
      </div>)}
    </div>}
  </section>;
}
