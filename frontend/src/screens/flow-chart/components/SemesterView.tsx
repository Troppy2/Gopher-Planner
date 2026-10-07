import type { ReactNode } from "react";
import { AlertTriangle, CheckCircle2, Plus, X } from "lucide-react";
import type { Course, Plan, Profile } from "@/api/types";
import { Button, ProgressBar, StatusBadge } from "@/ui";
import { credits } from "@/lib/format";
import { eligible, firstFutureIndex, lastPlanIndex, projectedCredits, sumCredits } from "@/features/plan/planRules";

interface Props {
  plan: Plan;
  profile: Profile;
  courses: Course[];
  goal: number;
  onOpen: (code: string) => void;
  onAdd: (code: string, termIdx: number) => void;
  onRemove: (code: string, termIdx: number) => void;
}

function Row({ c, onOpen, right }: { c: Course; onOpen: (code: string) => void; right: ReactNode }) {
  return (
    <li className="semrow hover-row">
      <button type="button" className="semrow-main" onClick={() => onOpen(c.code)}>
        <b>{c.code}</b>
        <span>{c.title}</span>
        {c.lockReason && (
          <span className="semnote">
            <AlertTriangle className="ic sm" aria-hidden />
            {c.lockReason}
          </span>
        )}
      </button>
      <span className="num muted semcr">{credits(c.credits)}</span>
      {right}
    </li>
  );
}

export function SemesterView({ plan, profile, courses, goal, onOpen, onAdd, onRemove }: Props) {
  const current = courses.filter((c) => c.status === "prog");
  const first = firstFutureIndex(plan);
  const last = lastPlanIndex(plan, profile);
  const projected = projectedCredits(plan.baseCredits, courses);
  const short = goal - projected;
  const gradTerm = plan.terms[last];

  return (
    <div className="sem">
      <section className="semcard surf" id="sem-current" aria-labelledby="semh-current">
        <div className="semhead">
          <h2 id="semh-current" tabIndex={-1}>
            {plan.currentTerm}, current classes
          </h2>
          <span className="semmeta num">{credits(sumCredits(current))}</span>
        </div>
        <ul>
          {current.map((c) => (
            <Row key={c.code} c={c} onOpen={onOpen} right={<StatusBadge status="prog" />} />
          ))}
        </ul>
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
                    right={
                      <Button variant="ghost" size="sm" onClick={() => onRemove(c.code, i)} aria-label={`Remove ${c.code} from ${term}`}>
                        <X className="ic sm" aria-hidden />
                        Remove
                      </Button>
                    }
                  />
                ))}
                {locked.map((c) => (
                  <Row key={c.code} c={c} onOpen={onOpen} right={<StatusBadge status="block" />} />
                ))}
              </ul>
            ) : (
              <p className="muted sempad">Nothing planned for {term}.</p>
            )}
            <h3 className="semsub">Courses you could take</h3>
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
