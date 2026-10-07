import type { Course } from "@/api/types";
import { Button, StatusBadge } from "@/ui";

interface Props {
  courses: Course[];
  onOpen: (code: string) => void;
  onAdd: (code: string) => void;
}

export function ResultsList({ courses, onOpen, onAdd }: Props) {
  return (
    <>
      <div className="chead" aria-hidden>
        <span>Course</span>
        <span>Credits</span>
        <span>Offered</span>
        <span>Requirement</span>
        <span>Status</span>
        <span />
      </div>
      <ul className="surf clist">
        {courses.map((c) => (
          <li key={c.code} className="citem">
            <button type="button" className="cm" onClick={() => onOpen(c.code)}>
              <b>{c.code}</b>
              <span>{c.title}</span>
            </button>
            <span className="c-cr num">
              <span className="mlab">Credits </span>
              {c.credits}
            </span>
            <span className="c-off">
              <span className="mlab">Offered </span>
              {c.offered.join(", ")}
            </span>
            <span className="c-req">{c.requirement}</span>
            <span className="c-st">
              <StatusBadge status={c.status} />
            </span>
            <span className="acts">
              <Button variant="ghost" size="sm" className="view-btn" onClick={() => onOpen(c.code)} aria-label={`View details for ${c.code}`}>
                View details
              </Button>
              {c.status === "avail" ? (
                <Button size="sm" onClick={() => onAdd(c.code)} aria-label={`Add ${c.code} to plan`}>
                  Add to plan
                </Button>
              ) : (
                <span className="acts-pad" />
              )}
            </span>
          </li>
        ))}
      </ul>
    </>
  );
}
