import { useEffect, useRef, useState } from "react";
import { Link } from "react-router";
import { useQuery } from "@tanstack/react-query";
import { ChevronDown } from "lucide-react";
import { getOptions } from "@/api/endpoints";
import { queryKeys } from "@/api/queryKeys";
import { Button, EmptyState, Modal, SegmentedControl, Skeleton, SkeletonRegion } from "@/ui";
import { usePlan } from "@/features/plan/usePlan";
import { targetTerm } from "@/features/plan/planRules";
import { UnverifiedMajorNote } from "@/features/profile/profileRules";
import { PlanWarnings } from "@/features/plan/PlanWarnings";
import { useRequirementsParam } from "./useRequirementsParam";
import { buildTree } from "./buildTree";
import type { RequirementTree } from "./buildTree";
import { chip } from "./status";
import { Notes, RequirementNode } from "./RequirementNode";
import { ReportProblemButton } from "@/features/reports/ReportProblemButton";
import "./requirements.css";
function Group({ group, focused, hasFocus, ...props }: { group: RequirementTree; focused: boolean; hasFocus: boolean } & Omit<Parameters<typeof RequirementNode>[0], 'node' | 'groupLabel'>) {
  const status = chip(group.completedStatus,group.projectedStatus);
  const [expanded,setExpanded]=useState(focused || (!hasFocus && status.cls==='short'));
  const header=useRef<HTMLButtonElement>(null);
  useEffect(()=>{ if (focused) { setExpanded(true); const frame=requestAnimationFrame(()=>{ header.current?.focus({preventScroll:true}); header.current?.scrollIntoView({block:'nearest'}); }); return ()=>cancelAnimationFrame(frame); } },[focused]);
  return <section className="requirements-group"><h3><button ref={header} type="button" className="requirements-group-header" aria-expanded={expanded} aria-controls={`requirements-${group.id}`} onClick={()=>setExpanded(!expanded)}>
    <ChevronDown className="ic sm" aria-hidden /><span>{group.label}{" "}<small>{group.category}</small></span>{" "}
    <span className={`req-st ${status.cls}`}><status.Icon className="ic sm" aria-hidden />{status.text}</span>
  </button></h3>
    {expanded && <div id={`requirements-${group.id}`} className="requirements-group-body"><Notes items={group.details} />{group.children.map(child=><RequirementNode key={child.id} node={child} root groupLabel={group.label} {...props} satisfied={group.projectedStatus==='satisfied'} />)}
      <div className="requirements-report"><span className="muted">Something wrong with this requirement?</span><ReportProblemButton target={{ type: "requirement", requirementId: group.id, label: group.label }} /></div></div>}
  </section>;
}
function Content() {
  const {groupId,openCourse}=useRequirementsParam();
  const {plan,profile,courses,isLoading,error,refetch,add,announce,announcement}=usePlan();
  const {data:options}=useQuery({queryKey:queryKeys.options,queryFn:getOptions});
  const [filter,setFilter]=useState<'all'|'needed'>('all');
  const groups=buildTree(plan?.requirementProgress ?? []);
  const focused=groups.some(g=>g.id===groupId) ? groupId : null;
  const addCourse=(code:string)=>{
    const course=courses.find(c=>c.code===code);
    if (!plan || !course) return;
    const {term}=targetTerm(course,courses,plan,profile);
    if (!term) { openCourse(code); return; }
    add(code,term); announce(`${code} added to ${term}.`);
  };
  const visible=groups.filter(g=>filter==='all' || ['short','review'].includes(chip(g.completedStatus,g.projectedStatus).cls));
  return <>
    <div className="requirements-filter">
      <div className="requirements-summary">{(['met','track','review','short'] as const).map(cls=>{
        const s=chip(cls==='met'?'satisfied':'unsatisfied',cls==='track'?'satisfied':cls==='review'?'needs_review':'unsatisfied');
        const count=groups.filter(g=>chip(g.completedStatus,g.projectedStatus).cls===cls).length;
        return <span key={cls} className={`req-st ${count ? cls : 'zero'}`}><s.Icon className="ic sm" aria-hidden />{s.text} {count}</span>;
      })}</div>
      <SegmentedControl label="Requirements filter" value={filter} onChange={setFilter} options={[{value:'all',label:'All'},{value:'needed',label:'Still needed'}]} />
    </div>
    <div className="requirements-body"><UnverifiedMajorNote options={options} major={profile?.major ?? ''} />
      <p className="muted requirements-caveat">Your advisor and APAS have the final word.</p>
      <p className="vh" role="status" aria-live="polite">{announcement}</p>
      {isLoading ? <SkeletonRegion label="requirements">{[0,1,2].map(i=><div className="requirements-skeleton" key={i}><Skeleton width="65%" height={24}/><Skeleton height={44}/></div>)}</SkeletonRegion>
      : error ? <EmptyState title="We couldn't load your plan" action={<Button onClick={()=>refetch()}>Try again</Button>} />
      : !groups.length ? <EmptyState title={plan?.catalogTerm===null && plan.availableCatalogTerms.length ? 'Choose a catalog year to see your requirements' : "Requirement details aren't available for your major yet."}>
        {plan?.catalogTerm===null && plan.availableCatalogTerms.length ? <Link to="/flow-chart">Choose your catalog year</Link> : null}
      </EmptyState> : <>{visible.map(group=><Group key={group.id} group={group} focused={focused===group.id} hasFocus={!!focused} courses={courses} stillNeeded={filter==='needed'} openCourse={openCourse} addCourse={addCourse} />)}{!visible.length && <p>All requirements are met or on track.</p>}</>}
      {plan && <PlanWarnings warnings={plan.warnings} />}
    </div>
  </>;
}
export function RequirementsModal() {
  const {isOpen,close,groupId}=useRequirementsParam();
  return isOpen ? <OpenModal close={close} groupId={groupId} /> : null;
}
function OpenModal({close,groupId}:{close:()=>void;groupId:string|null}) {
  const {plan,profile}=usePlan();
  return <Modal open onOpenChange={open=>{if(!open)close();}} title="Degree requirements" subtitle={<>{profile?.major}{plan?.catalogTerm && ` · Catalog year ${plan.catalogTerm}`}</>} size="lg" flush initialFocus="dialog"><Content key={groupId} /></Modal>;
}

