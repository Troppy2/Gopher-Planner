import { useState } from "react";
import { CalendarDays, Check, Clock, Lock, Plus } from "lucide-react";
import type { Course } from "@/api/types";
import { Button, Callout } from "@/ui";
import { credits } from "@/lib/format";
import type { RequirementTree } from "./buildTree";
interface Props { node: RequirementTree; courses: Course[]; stillNeeded: boolean; satisfied?: boolean; groupLabel: string; openCourse: (code: string) => void; addCourse: (code: string) => void }
const placed = (course?: Course) => !!course && ['done', 'prog', 'plan'].includes(course.status);
function CourseRow({ code, courses, stillNeeded, satisfied, openCourse, addCourse }: Omit<Props, 'node' | 'groupLabel'> & {code: string}) {
  const course = courses.find(c => c.code === code);
  if (stillNeeded && placed(course)) return null;
  if (!course) return <li className="requirements-course muted">{code}</li>;
  const Icon = { done: Check, prog: Clock, plan: CalendarDays, avail: Plus, block: Lock }[course.status];
  const status = { done: 'Done', prog: 'In progress', plan: `Planned, ${course.term}`, avail: 'Needed', block: 'Locked' }[course.status];
  return <li className="requirements-course"><div className="requirements-course-name">
    <a href={`?course=${encodeURIComponent(code)}`} onClick={e => { e.preventDefault(); openCourse(code); }}>{code}</a>
    <span>{course.title}</span><span className="muted">{credits(course.credits)}</span>
  </div><span className={`badge b-${course.status}`}><Icon className="ic sm" aria-hidden />{status}</span>
    {course.status === 'avail' && !satisfied && <Button variant="ghost" size="sm" aria-label={`Add ${code} to plan`} onClick={() => addCourse(code)}>Add to plan</Button>}
    {course.status === 'block' && <Button variant="ghost" size="sm" aria-label={`Why is ${code} locked?`} onClick={() => openCourse(code)}>Why?</Button>}
  </li>;
}
function Options({ node, ...props }: Props) {
  const [showAll, setShowAll] = useState(false);
  const [filter, setFilter] = useState('');
  const options = node.options ?? [];
  const priority = (code: string) => node.projectedEvidence.matchedCodes.includes(code) || placed(props.courses.find(c => c.code === code));
  const first = options.filter(priority);
  const rest = options.filter(code => !priority(code));
  const sorted = [...first, ...rest];
  const filtered = sorted.filter(code => {
    const course = props.courses.find(c => c.code === code);
    return (!props.stillNeeded || !placed(course)) && `${code} ${course?.title ?? ''}`.toLowerCase().includes(filter.toLowerCase());
  });
  const visible = showAll || filter ? filtered : filtered.filter(code => priority(code)).concat(filtered.filter(code => !priority(code)).slice(0,12));
  return <div>{options.length > 30 && <label className="requirements-search">Filter courses<input value={filter} onChange={e=>setFilter(e.target.value)} placeholder="Code or title" /></label>}
    <ul className="requirements-courses">{visible.map(code => <CourseRow key={code} code={code} {...props} />)}</ul>
    {visible.length < filtered.length && <Button variant="ghost" size="sm" onClick={()=>setShowAll(true)}>Show all {options.length} courses</Button>}
    {!filtered.length && <p className="muted">No courses match this filter.</p>}
  </div>;
}
export function RequirementNode({ node, ...props }: Props) {
  const satisfied = props.satisfied || node.projectedStatus === 'satisfied';
  const next = { ...props, satisfied };
  const e = node.projectedEvidence;
  let heading = '';
  if (node.type === 'all') heading = 'Complete all of these';
  if (node.type === 'any') heading = 'Complete one option';
  if (node.type === 'count') heading = e.minCourses !== undefined ? `Choose ${e.minCourses} of these ${node.options?.length ?? 0}` : `Up to ${e.maxCourses} of these count`;
  if (node.type === 'credits') heading = `Earn ${e.requiredCredits} credits from these courses`;
  return <div className="requirements-rule">
    {heading && <h4>{heading}{node.projectedStatus === 'satisfied' && <span className="badge b-done"><Check className="ic sm" aria-hidden />Met</span>}</h4>}
    {node.label !== props.groupLabel && node.type !== 'course' && node.type !== 'review' && <p className="muted">{node.label}</p>}
    {node.type === 'count' && e.minCourses !== undefined && <p>{e.matchedCourses} of {e.minCourses} chosen</p>}
    {node.type === 'credits' && <p>{e.matchedCredits} of {e.requiredCredits} credits</p>}
    {node.type === 'review' ? <Callout tone="warn" title="Check this one with your advisor">{node.details.map((d,i)=><p key={i}>{d}</p>)}</Callout> : node.details.length > 0 && <div className="requirements-details">{node.details.map((d,i)=><p key={i}>{e.appliedAdjustments.length > 0 ? 'Adjusted: ' : ''}{d}</p>)}</div>}
    {node.type === 'course' && <ul className="requirements-courses"><CourseRow code={node.label} {...next} /></ul>}
    {(node.type === 'count' || node.type === 'credits') && <Options node={node} {...next} />}
    {node.children.map((child,i) => node.type === 'any' ? <section className="requirements-option" key={child.id}>
      <h5>{child.label !== props.groupLabel ? child.label : `Option ${i+1}`}</h5>
      {child.projectedEvidence.matchedCodes.length > 0 && <span className="badge b-plan"><Check className="ic sm" aria-hidden />Counting toward this</span>}
      <RequirementNode node={child} {...next} />
    </section> : <RequirementNode key={child.id} node={child} {...next} />)}
  </div>;
}
