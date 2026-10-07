import { ExternalLink, Plus } from "lucide-react";
import { Button, Callout, Drawer, StatusBadge } from "@/ui";
import { usePlan } from "@/features/plan/usePlan";
import { targetTerm } from "@/features/plan/planRules";
import { useCourseParam } from "./useCourseParam";
import "./course-detail.css";

export function CourseDrawer() {
  const { code, close } = useCourseParam();
  const { courses, plan, profile, add, remove } = usePlan();
  const course = code ? courses.find((c) => c.code === code) : undefined;

  if (!course || !plan) return null;

  const target = course.status === "avail" ? targetTerm(course, courses, plan, profile) : null;
  const rmpQuery = encodeURIComponent(course.professors[0] ?? "University of Minnesota");

  let note = null;
  let action = null;
  if (course.status === "block") {
    note = <Callout tone="warn" title="Locked for you right now">{course.lockReason}</Callout>;
  } else if (target?.term) {
    note = (
      <Callout tone="ok" title={`Prerequisites are met by ${target.term}`}>
        Adding puts it in {target.term}. Nothing is saved until you press Save plan.
      </Callout>
    );
    const term = target.term;
    action = (
      <Button
        onClick={() => {
          add(course.code, term);
          close();
        }}
      >
        <Plus className="ic sm" aria-hidden />
        Add to {term}
      </Button>
    );
  } else if (target) {
    note = target.missing.length ? (
      <Callout tone="warn" title="Prerequisite conflict">
        {target.missing.join(", ")} {target.missing.length > 1 ? "are" : "is"} not in your plan yet. Add {target.missing.length > 1 ? "them" : "it"} first.
      </Callout>
    ) : (
      <Callout tone="info" title="No open term">
        It isn't offered in a term before your graduation target.
      </Callout>
    );
    action = <Button disabled>Add to plan</Button>;
  } else if (course.status === "plan") {
    action = (
      <Button
        variant="ghost"
        onClick={() => {
          remove(course.code);
          close();
        }}
      >
        Remove from plan
      </Button>
    );
  }

  return (
    <Drawer
      open
      onOpenChange={(o) => !o && close()}
      title={course.code}
      subtitle={course.title}
      closeLabel="Close details"
      footer={
        <>
          {action}
          <Button variant="ghost" onClick={close}>
            Close
          </Button>
        </>
      }
    >
      <div>
        <StatusBadge status={course.status} />
      </div>
      {note}
      <dl className="facts">
        <div>
          <dt>Credits</dt>
          <dd className="num">{course.credits}</dd>
        </div>
        <div>
          <dt>Offered</dt>
          <dd>{course.offered.join(", ")}</dd>
        </div>
        <div>
          <dt>Requirement</dt>
          <dd>{course.requirement}</dd>
        </div>
        <div>
          <dt>Term</dt>
          <dd>{course.term ?? "Not placed"}</dd>
        </div>
      </dl>
      <section>
        <h3 className="dsub">Prerequisites</h3>
        {course.prereqs.length ? (
          <ul className="dlist">
            {course.prereqs.map((p) => {
              const q = courses.find((c) => c.code === p);
              return (
                <li key={p}>
                  <span>
                    <b>{p}</b> {q?.title}
                  </span>
                  {q ? <StatusBadge status={q.status} /> : <span className="muted">Not tracked</span>}
                </li>
              );
            })}
          </ul>
        ) : (
          <p className="muted">None.</p>
        )}
      </section>
      <section>
        <h3 className="dsub">Concurrent requirements</h3>
        {course.concurrent.length ? (
          <ul className="dlist">
            {course.concurrent.map((c) => (
              <li key={c}>
                <span>
                  <b>{c}</b> taken in the same term
                </span>
              </li>
            ))}
          </ul>
        ) : (
          <p className="muted">None listed.</p>
        )}
      </section>
      <section>
        <h3 className="dsub">Historical professors</h3>
        <ul className="dlist">
          {course.professors.map((p) => (
            <li key={p}>
              <span>{p}</span>
            </li>
          ))}
        </ul>
      </section>
      <div className="dlinks">
        <a className="btn ghost sm" href="https://umn.lol" target="_blank" rel="noopener noreferrer">
          Gopher Grades
          <ExternalLink className="ic sm" aria-hidden />
        </a>
        <a
          className="btn ghost sm"
          href={`https://www.ratemyprofessors.com/search/professors?q=${rmpQuery}`}
          target="_blank"
          rel="noopener noreferrer"
        >
          Rate My Professors
          <ExternalLink className="ic sm" aria-hidden />
        </a>
      </div>
    </Drawer>
  );
}
