import { useState } from "react";
import { useInfiniteQuery } from "@tanstack/react-query";
import type { Course, Plan, Profile } from "@/api/types";
import { getCourses } from "@/api/endpoints";
import { Button } from "@/ui";
import { catalogToPlanCourse, swapReason } from "@/features/plan/planRules";
import { TermPicker } from "@/features/plan/TermPicker";
import { CreditsField } from "@/features/plan/CreditsField";
import "./plan-course-actions.css";

interface Props {
  course: Course;
  courses: Course[];
  plan: Plan;
  profile: Profile;
  onMove: (code: string, term: string) => void;
  onRemove: (code: string) => void;
  onSwap: (code: string, replacement: Course) => void;
  announce: (message: string) => void;
  onCredits?: (code: string, credits: number) => void;
}

export function PlanCourseActions({ course, courses, plan, profile, onMove, onRemove, onSwap, announce, onCredits }: Props) {
  const [showSwaps, setShowSwaps] = useState(false);
  const categories = course.slotCategories?.length ? course.slotCategories : [course.slot ?? ""];
  const alternatives = useInfiniteQuery({
    queryKey: ["slot-alternatives", categories],
    initialPageParam: 0,
    queryFn: ({ pageParam }) => getCourses({ le: categories, limit: 100, offset: pageParam }),
    getNextPageParam: last => last.offset + last.limit < last.total ? last.offset + last.limit : undefined,
    enabled: showSwaps && !!course.slot,
  });
  const options = (alternatives.data?.pages.flatMap(p => p.courses) ?? []).filter(c => categories.every(category => c.leAttributes?.includes(category)) &&
    !courses.some(existing => existing.code === c.code && ["done", "prog", "plan"].includes(existing.status)));
  return <section className="plan-actions" aria-label={`Plan actions for ${course.code}`}>
    <h3 className="dsub">Edit class</h3>
    <TermPicker course={course} courses={courses} plan={plan} profile={profile} onMove={onMove} announce={announce} />
    {course.status === "prog" && onCredits && <CreditsField code={course.code} credits={course.credits} onChange={onCredits} />}
    <Button variant="ghost" onClick={() => { onRemove(course.code); announce(`${course.code} removed from plan.`); }}>Remove from plan</Button>
    {course.slot && <>
      <Button variant="ghost" aria-expanded={showSwaps} onClick={() => setShowSwaps(!showSwaps)}>Swap suggestion</Button>
      {showSwaps && <div>
        {alternatives.isPending && <p role="status">Loading suggestions...</p>}
        {alternatives.isError && <p>Could not load suggestions. <Button onClick={() => void alternatives.refetch()}>Try again</Button></p>}
        {alternatives.isSuccess && !options.length && <p>No other suggestions available.</p>}
        <ul className="plan-action-list">{options.map(item => {
          const replacement = catalogToPlanCourse(item);
          const reason = replacement.status === "block" ? replacement.lockReason : swapReason(course, replacement, courses, plan.terms, profile.creditLoad);
          return <li key={item.code}><Button variant="ghost" disabled={!!reason} onClick={() => {
            onSwap(course.code, replacement);
            announce(`${course.code} replaced with ${item.code}. Gen ed: ${course.slot}.`);
          }}>{item.code}: {item.title}{reason ? `: ${reason}` : ""}</Button></li>;
        })}</ul>
        {alternatives.hasNextPage && <Button disabled={alternatives.isFetchingNextPage} onClick={() => void alternatives.fetchNextPage()}>
          {alternatives.isFetchingNextPage ? "Loading more..." : "More suggestions"}
        </Button>}
      </div>}
    </>}
  </section>;
}
