import type { Course } from "@/api/types";
import { StatusBadge } from "@/ui";
import { useCourseParam } from "@/features/course-detail/useCourseParam";
import { credits } from "@/lib/format";

export function CourseList({ courses }: { courses: Course[] }) {
  const { open } = useCourseParam();
  return (
    <ul className="clist-d">
      {courses.map((c) => (
        <li key={c.code}>
          <button className="crow hover-row" onClick={() => open(c.code)}>
            <span className="crow-main">
              <b>{c.code}</b>
              <span className="crow-t">{c.title}</span>
            </span>
            <span className="crow-meta">
              <span className="num">{credits(c.credits)}</span>
              <StatusBadge status={c.status} />
            </span>
          </button>
        </li>
      ))}
    </ul>
  );
}
