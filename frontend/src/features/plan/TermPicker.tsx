import type { Course, Plan, Profile } from "@/api/types";
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
  return <label className="term-picker">
    <span>Semester</span>
    <select aria-label={`Move ${course.code} to semester`} value={course.term ?? ""} onChange={event => {
      const picker = event.currentTarget;
      onMove(course.code, event.target.value);
      announce?.(`${course.code} moved to ${event.target.value}.`);
      requestAnimationFrame(() => {
        const target = picker.isConnected ? picker : Array.from(document.querySelectorAll("select")).find(
          select => select.getAttribute("aria-label") === `Move ${course.code} to semester`);
        target?.focus({ preventScroll: true });
      });
    }}>
      {plan.terms.slice(first, lastPlanIndex(plan, profile) + 1).map(term => {
        const reason = term === course.term ? null : moveReason(course, plan.terms.indexOf(term), courses, plan.terms, profile.creditLoad);
        return <option key={term} value={term} disabled={!!reason}>{term === plan.currentTerm ? `${term} (current)` : term}{reason ? `: ${reason}` : ""}</option>;
      })}
    </select>
  </label>;
}
