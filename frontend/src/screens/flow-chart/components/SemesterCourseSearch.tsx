import { useId, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Plus, X } from "lucide-react";
import { getCourses } from "@/api/endpoints";
import type { Course, Plan, Profile } from "@/api/types";
import { catalogToPlanCourse, moveReason } from "@/features/plan/planRules";
import { Button, CourseRowsSkeleton, SkeletonRegion } from "@/ui";

export function SemesterCourseSearch({ term, plan, profile, courses, onAdd }: {
  term: string; plan: Plan; profile: Profile; courses: Course[]; onAdd: (course: Course, term: string) => void;
}) {
  const [open, setOpen] = useState(false), [query, setQuery] = useState("");
  const id = useId();
  const search = useQuery({ queryKey: ["semester-course-search", query], queryFn: () => getCourses({ q: query, limit: 6 }), enabled: open && query.trim().length > 1 });
  return <div className="semester-add">
    <Button variant="ghost" size="sm" aria-label={`Add class to ${term}`} aria-expanded={open} onClick={() => setOpen(!open)}>
      {open ? <X className="ic sm" aria-hidden /> : <Plus className="ic sm" aria-hidden />}{open ? "Close search" : "Add class"}
    </Button>
    {open && <div className="semester-search">
      <label htmlFor={id}>Find a class for {term}</label>
      <div className="inline-search"><input id={id} autoFocus className="input" value={query} onChange={e => setQuery(e.target.value)} placeholder="Course code or title" /></div>
      {query.trim().length > 1 && <>
        {search.isPending && <SkeletonRegion label="class search"><CourseRowsSkeleton rows={2} /></SkeletonRegion>}
        {search.isError && <p role="alert">Could not load classes. <Button size="sm" onClick={() => void search.refetch()}>Try again</Button></p>}
        {search.isSuccess && !search.data.courses.length && <p className="muted">No matching classes.</p>}
        <ul className="semester-results">{search.data?.courses.map(item => {
          const existing = courses.find(c => c.code === item.code);
          const course = existing ?? catalogToPlanCourse(item);
          const reason = existing && ["done", "prog", "plan"].includes(existing.status) ? "Already in your coursework or plan" :
            course.status === "block" ? "Prerequisites need review" : moveReason(course, plan.terms.indexOf(term), [...courses.filter(c => c.code !== course.code), course], plan.terms, profile.creditLoad);
          return <li key={item.code}><div><b>{item.code}</b><span>{item.title}</span>{reason && <small>{reason}</small>}</div>
            <Button size="sm" variant="ghost" disabled={!!reason} onClick={() => { onAdd(course, term); setQuery(""); setOpen(false); }}>Add<span className="vh"> {item.code} to {term}</span></Button></li>;
        })}</ul>
      </>}
    </div>}
  </div>;
}
