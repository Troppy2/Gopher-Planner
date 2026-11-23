import type { Course, Plan, Profile } from "@/api/types";
import { Select } from "@/ui/Select";
import { lastPlanIndex, moveReason } from "./planRules";
import "./term-picker.css";

interface Props {
  course: Course;
  courses: Course[];
  plan: Plan;
  profile: Profile;
  onMove: (code: string, term: string) => void;
  announce?: (message: string) => void;
}

export function TermPicker({ course, courses, plan, profile, onMove, announce }: Props) {
  const first = plan.terms.indexOf(plan.currentTerm);
  const options = plan.terms.slice(first, lastPlanIndex(plan, profile) + 1).map(term => {
    const reason = term === course.term ? null : moveReason(course, plan.terms.indexOf(term), courses, plan.terms, profile.creditLoad);
    return { value: term, label: term === plan.currentTerm ? `${term} (current)` : term, hint: reason ?? undefined, disabled: !!reason };
  });
  return <Select className="term-picker" ariaLabel={`Move ${course.code} to semester`} value={course.term ?? ""} options={options}
    onChange={term => { onMove(course.code, term); announce?.(`${course.code} moved to ${term}.`); }} />;
}
