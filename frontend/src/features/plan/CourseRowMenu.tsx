import * as Menu from "@radix-ui/react-dropdown-menu";
import { ArrowRightLeft, ChevronRight, MoreHorizontal, Trash2 } from "lucide-react";
import type { Course, Plan, Profile } from "@/api/types";
import { lastPlanIndex, moveReason } from "./planRules";

interface Props {
  course: Course;
  courses: Course[];
  plan: Plan;
  profile: Profile;
  onMove: (code: string, term: string) => void;
  onRemove: () => void;
}

/** One compact menu per plan row: move to another semester, or remove. */
export function CourseRowMenu({ course, courses, plan, profile, onMove, onRemove }: Props) {
  return <Menu.Root>
    <Menu.Trigger className="icon-btn" aria-label={`Options for ${course.code}`}>
      <MoreHorizontal className="ic" aria-hidden />
    </Menu.Trigger>
    <Menu.Portal>
      <Menu.Content className="menu" align="end" sideOffset={6}>
        <Menu.Sub>
          <Menu.SubTrigger className="menu-item">
            <ArrowRightLeft className="ic sm" aria-hidden />
            <span className="menu-grow">Move to…</span>
            <ChevronRight className="ic sm" aria-hidden />
          </Menu.SubTrigger>
          <Menu.Portal>
            <Menu.SubContent className="menu" sideOffset={4}>
              <MoveOptions course={course} courses={courses} plan={plan} profile={profile} onMove={onMove} />
            </Menu.SubContent>
          </Menu.Portal>
        </Menu.Sub>
        <Menu.Item className="menu-item menu-danger" onSelect={onRemove}>
          <Trash2 className="ic sm" aria-hidden />
          Remove from {course.term}
        </Menu.Item>
      </Menu.Content>
    </Menu.Portal>
  </Menu.Root>;
}

/** Rendered only while "Move to…" is open, so move checks don't run for every row on every render. */
function MoveOptions({ course, courses, plan, profile, onMove }: Omit<Props, "onRemove">) {
  const first = plan.terms.indexOf(plan.currentTerm);
  const terms = plan.terms.slice(first, lastPlanIndex(plan, profile) + 1).filter(t => t !== course.term);
  return <>{terms.map(term => {
    const reason = moveReason(course, plan.terms.indexOf(term), courses, plan.terms, profile.creditLoad);
    return <Menu.Item key={term} className="menu-item menu-item-stack" disabled={!!reason} onSelect={() => onMove(course.code, term)}>
      <span>{term === plan.currentTerm ? `${term} (current)` : term}</span>
      {reason && <span className="sel-hint">{reason}</span>}
    </Menu.Item>;
  })}</>;
}
