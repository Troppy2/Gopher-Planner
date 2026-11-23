import type { ReactNode } from "react";
import { AlertTriangle, CheckCircle2, Plus, X } from "lucide-react";
import type { Course, Plan, Profile } from "@/api/types";
import { Button, ProgressBar, StatusBadge } from "@/ui";
import { credits } from "@/lib/format";
import { SlotTag } from "@/features/plan/PlanLabels";
import { TermPicker } from "@/features/plan/TermPicker";
import { CreditsField } from "@/features/plan/CreditsField";
import { SemesterCourseSearch } from "./SemesterCourseSearch";
import { eligible, firstFutureIndex, lastPlanIndex, projectedCredits, sumCredits } from "@/features/plan/planRules";

interface Props {
  plan: Plan;
  profile: Profile;
  courses: Course[];
  goal: number;
  onOpen: (code: string) => void;
  onAdd: (code: string, termIdx: number) => void;
  onRemove: (code: string, termIdx: number) => void;
  onCredits?: (code: string, credits: number) => void;
  onAddCourse?: (course: Course, term: string) => void;
}

function Row({ c, onOpen, right, hideCredits = false, showStatus = false }: { c: Course; onOpen: (code: string) => void; right: ReactNode; hideCredits?: boolean; showStatus?: boolean }) {
  return (
    <li className="semrow hover-row">
      <button type="button" className="semrow-main" onClick={() => onOpen(c.code)}>
        <b>{c.code}</b>
        {showStatus && <StatusBadge status={c.status} />}
        <span>{c.title}</span>
        <SlotTag slot={c.slot} />
        {c.lockReason && (
          <span className="semnote">
            <AlertTriangle className="ic sm" aria-hidden />
            {c.lockReason}
          </span>
        )}
      </button>
      {!hideCredits && <span className="num muted semcr">{credits(c.credits)}</span>}
      {right}
    </li>
  );
}

export function SemesterView({ plan, profile, courses, goal, onOpen, onAdd, onRemove, onCredits, onAddCourse }: Props) {
  const current = courses.filter((c) => c.status === "prog" || (c.status === "plan" && c.term === plan.currentTerm));
  const first = firstFutureIndex(plan);
  const last = lastPlanIndex(plan, profile);
  const projected = projectedCredits(plan.baseCredits, courses);
  const short = goal - projected;
  const gradTerm = plan.terms[last];
  const controls = (c: Course) => <div className="semester-controls">
    {c.status === "prog" && onCredits && <CreditsField code={c.code} credits={c.credits} onChange={onCredits} />}
    <TermPicker course={c} courses={courses} plan={plan} profile={profile} onMove={(code, term) => onAdd(code, plan.terms.indexOf(term))} />
    <Button variant="ghost" size="sm" aria-label={`Remove ${c.code} from ${c.term}`} onClick={() => onRemove(c.code, plan.terms.indexOf(c.term!))}><X className="ic sm" aria-hidden /></Button>
  </div>;
  const search = (term: string) => <SemesterCourseSearch term={term} plan={plan} profile={profile} courses={courses}
    onAdd={(course, target) => onAddCourse ? onAddCourse(course, target) : onAdd(course.code, plan.terms.indexOf(target))} />;

  return (
    <div className="sem">
      <section className="semcard surf" id="sem-current" aria-labelledby="semh-current">
        <div className="semhead">
          <h2 id="semh-current" tabIndex={-1}>
            {plan.currentTerm}, current classes
          </h2>
          <span className="semmeta num">{sumCredits(current)} of {profile.creditLoad} credits</span>
        </div>
        <ProgressBar label={`${plan.currentTerm} credits`} value={sumCredits(current)} max={profile.creditLoad} over={sumCredits(current) > profile.creditLoad} />
        <ul>
          {current.map((c) => (
            <Row key={c.code} c={c} onOpen={onOpen} right={controls(c)} hideCredits={c.status === "prog" && !!onCredits} showStatus />
          ))}
        </ul>
        {!current.length && <p className="muted">No current classes. Add a class or move one into this semester.</p>}
        {search(plan.currentTerm)}
      </section>

      {Array.from({ length: last - first + 1 }, (_, k) => first + k).map((i) => {
        const term = plan.terms[i];
        const planned = courses.filter((c) => c.term === term && c.status === "plan");
        const locked = courses.filter((c) => c.term === term && c.status === "block");
        const options = courses.filter((c) => eligible(c, i, courses, plan.terms)).slice(0, 4);
        const cr = sumCredits(planned);
        const over = cr > profile.creditLoad;
        return (
          <section key={term} className="semcard surf" id={`sem-${i}`} aria-labelledby={`semh-${i}`}>
            <div className="semhead">
              <h2 id={`semh-${i}`} tabIndex={-1}>
                {term}
              </h2>
              <span className={over ? "semmeta num over" : "semmeta num"}>
                {over && <AlertTriangle className="ic sm" aria-hidden />}
                {cr} of {profile.creditLoad} credits{over ? `, over by ${cr - profile.creditLoad}` : ""}
              </span>
            </div>
            <ProgressBar label={`${term} credits`} value={cr} max={profile.creditLoad} over={over} />
            {planned.length || locked.length ? (
              <ul>
                {planned.map((c) => (
                  <Row
                    key={c.code}
                    c={c}
                    onOpen={onOpen}
                    right={controls(c)}
                  />
                ))}
                {locked.map((c) => (
                  <Row key={c.code} c={c} onOpen={onOpen} right={<StatusBadge status="block" />} />
                ))}
              </ul>
            ) : (
              <p className="muted sempad">Nothing planned for {term}.</p>
            )}
            {search(term)}
            <details className="semester-suggestions"><summary>Suggested classes</summary>
            {options.length ? (
              <ul>
                {options.map((c) => (
                  <Row
                    key={c.code}
                    c={c}
                    onOpen={onOpen}
                    right={
                      <Button variant="ghost" size="sm" onClick={() => onAdd(c.code, i)} aria-label={`Add ${c.code} to ${term}`}>
                        <Plus className="ic sm" aria-hidden />
                        Add
                      </Button>
                    }
                  />
                ))}
              </ul>
            ) : (
              <p className="muted">No other eligible courses this term.</p>
            )}
            </details>
          </section>
        );
      })}

      <section className="semcard surf" aria-labelledby="semh-grad">
        <div className="semhead">
          <h2 id="semh-grad">Graduation, {gradTerm}</h2>
          <span className="semmeta num">
            {projected} of {goal} credits
          </span>
        </div>
        <ProgressBar label="Projected credits at graduation" value={projected} max={goal} />
        {short > 0 ? (
          <p className="semnote big">
            <AlertTriangle className="ic sm" aria-hidden />
            {short} credits short of {goal}. Add courses to the semesters above.
          </p>
        ) : (
          <p className="semok">
            <CheckCircle2 className="ic sm" aria-hidden />
            This plan reaches {goal} credits by {gradTerm}.
          </p>
        )}
      </section>
    </div>
  );
}
