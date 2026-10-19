import type { CatalogCourse, Course } from "@/api/types";
import { Button, StatusBadge } from "@/ui";

interface CatalogRow extends CatalogCourse {
  planCourse?: Course;
}

interface Props {
  courses: CatalogRow[];
  onOpen: (code: string) => void;
  onAdd: (code: string) => void;
}

function formatCredits(course: CatalogCourse): string {
  if (course.minimumCredits === course.maximumCredits) {
    return String(course.minimumCredits);
  }

  return `${course.minimumCredits}–${course.maximumCredits}`;
}

function formatOffered(course: CatalogCourse): string {
  const offered = course.typicallyOffered.trim();

  if (!offered || offered === "-") {
    return "Not specified";
  }

  return offered;
}

export function ResultsList({ courses, onOpen, onAdd }: Props) {
  return (
    <>
      <div className="chead" aria-hidden="true">
        <span>Course</span>
        <span>Credits</span>
        <span>Offered</span>
        <span>Status</span>
        <span />
      </div>

      <ul className="surf clist">
        {courses.map((course) => {
          const status = course.planCourse?.status ?? "avail";

          return (
            <li key={course.code} className="citem">
              <button
                type="button"
                className="cm"
                onClick={() => onOpen(course.code)}
                aria-label={`${course.code}: ${course.title}. View course details`}
              >
                <b>{course.code}</b>
                <span>{course.title}</span>
              </button>

              <span className="c-cr num">
                <span className="mlab">Credits </span>
                {formatCredits(course)}
              </span>

              <span className="c-off">
                <span className="mlab">Offered </span>
                {formatOffered(course)}
              </span>

              <span className="c-st">
                <StatusBadge status={status} />
              </span>

              <span className="acts">
                <Button
                  variant="ghost"
                  size="sm"
                  className="view-btn"
                  onClick={() => onOpen(course.code)}
                  aria-label={`View details for ${course.code}`}
                >
                  View details
                </Button>

                {status === "avail" ? (
                  <Button
                    size="sm"
                    onClick={() => onAdd(course.code)}
                    aria-label={`Add ${course.code} to plan`}
                  >
                    Add to plan
                  </Button>
                ) : (
                  <span className="acts-pad" />
                )}
              </span>
            </li>
          );
        })}
      </ul>
    </>
  );
}
