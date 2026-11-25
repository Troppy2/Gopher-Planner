import type { Course } from "@/api/types";
import { StatusBadge } from "@/ui";
import { useCourseParam } from "@/features/course-detail/useCourseParam";
import { credits } from "@/lib/format";
import { SlotTag } from "@/features/plan/PlanLabels";

/** ``future``: the list is a later term, so in-progress courses there are registrations. */
export function CourseList({ courses, future = false }: { courses: Course[]; future?: boolean }) {
  const { open } = useCourseParam();
  return (
    <ul className="clist-d">
      {courses.map((c) => (
        <li key={c.code}>
          <button className="crow hover-row" onClick={() => open(c.code)}>
            <span className="crow-main">
              <b>{c.code}</b>
              <span className="crow-t">{c.title}</span>
              <SlotTag slot={c.slot} />
            </span>
            <span className="crow-meta">
              <span className="num">{credits(c.credits)}</span>
              <StatusBadge status={c.status} label={future && c.status === "prog" ? "Registered" : undefined} />
            </span>
          </button>
        </li>
      ))}
    </ul>
  );
}
