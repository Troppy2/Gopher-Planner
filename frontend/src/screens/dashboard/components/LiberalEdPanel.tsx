import { useState } from "react";
import { Link } from "react-router";
import { keepPreviousData, useQuery } from "@tanstack/react-query";
import { AlertCircle, CheckCircle2, ChevronDown, CircleDashed, HelpCircle, MinusCircle, Plus } from "lucide-react";
import type { LucideIcon } from "lucide-react";
import { getDoubleDippers } from "@/api/endpoints";
import { queryKeys } from "@/api/queryKeys";
import type { Course, LeCategory, LeCodes, LeItemStatus, LeSectionStatus, LiberalEd, Plan, Profile } from "@/api/types";
import { Button } from "@/ui";
import { catalogToPlanCourse, targetTerm } from "@/features/plan/planRules";
import { useCourseParam } from "@/features/course-detail/useCourseParam";

const ITEM: Record<LeItemStatus, { cls: string; text: string; Icon: LucideIcon }> = {
  done: { cls: "met", text: "Done", Icon: CheckCircle2 },
  in_progress: { cls: "track", text: "In progress", Icon: CircleDashed },
  planned: { cls: "track", text: "Planned", Icon: CircleDashed },
  needed: { cls: "short", text: "Needed", Icon: AlertCircle },
  needs_review: { cls: "review", text: "Needs review", Icon: HelpCircle },
  not_required: { cls: "review", text: "Not required", Icon: MinusCircle },
};

const SECTION: Record<LeSectionStatus, { cls: string; text: string; Icon: LucideIcon }> = {
  met: { cls: "met", text: "Met", Icon: CheckCircle2 },
  on_track: { cls: "track", text: "On track", Icon: CircleDashed },
  needs_review: { cls: "review", text: "Needs review", Icon: HelpCircle },
  short: { cls: "short", text: "Short", Icon: AlertCircle },
};

function Chip({ cls, text, Icon }: { cls: string; text: string; Icon: LucideIcon }) {
  return (
    <span className={`req-st ${cls}`}>
      <Icon className="ic sm" aria-hidden />
      {text}
    </span>
  );
}

const findLink = (designation: string) => `/catalog?le=${encodeURIComponent(designation)}`;

/** One line naming the courses behind a status, planned ones with their term. */
function evidence(codes: LeCodes, termOf: (code: string) => string | null) {
  const parts = [
    ...codes.done,
    ...codes.prog.map((code) => `${code} (in progress)`),
    ...codes.plan.map((code) => `${code} (${termOf(code) ?? "planned"})`),
  ];
  return parts.join(", ");
}

function CategoryRow({ item, termOf }: { item: LeCategory; termOf: (code: string) => string | null }) {
  const detail = item.source === "apas" ? "Complete on your APAS audit" : evidence(item.codes, termOf);
  return (
    <li className="req-row">
      <span className="req-name">
        <b>{item.label}</b>
        {detail && <span className="muted">{detail}</span>}
        {item.status === "needs_review" && <span className="muted">Your APAS audit doesn't show this yet. Check with your advisor.</span>}
        {item.status === "needed" && (
          <Link className="le-find" to={findLink(item.designations[0])}>
            Find {item.label} courses
          </Link>
        )}
      </span>
      <Chip {...ITEM[item.status]} />
    </li>
  );
}

/** A collapsible section: open when it needs attention, a one-line summary otherwise. */
function Section({ title, status, summary, children }: { title: string; status: LeSectionStatus; summary?: string; children: React.ReactNode }) {
  const id = `le-${title.toLowerCase().replace(/\W+/g, "-")}`;
  const [open, setOpen] = useState(status === "short" || status === "needs_review");
  return (
    <div className="le-section">
      <h3 className="le-h3">
        <button type="button" className="le-toggle" aria-expanded={open} aria-controls={`${id}-body`} onClick={() => setOpen(!open)}>
          <ChevronDown className="ic sm le-chev" aria-hidden />
          <span className="le-toggle-label">{title}</span>
          <Chip {...SECTION[status]} />
        </button>
      </h3>
      {summary && <p className="muted le-summary">{summary}</p>}
      {open && (
        <ul className="req-list" id={`${id}-body`}>
          {children}
        </ul>
      )}
    </div>
  );
}

function DoubleDippers({ liberal, plan, profile, courses, onAdd }: {
  liberal: LiberalEd;
  plan: Plan;
  profile?: Profile;
  courses: Course[];
  onAdd: (course: Course, term: string) => void;
}) {
  const [limit, setLimit] = useState(5);
  const [added, setAdded] = useState("");
  const course = useCourseParam();
  const taken = courses.filter((c) => c.status === "done" || c.status === "prog" || c.status === "plan").map((c) => c.code).sort();
  const enabled = liberal.remaining.length >= 2;
  const query = useQuery({
    queryKey: queryKeys.doubleDippers(liberal.remaining, taken, limit),
    queryFn: () => getDoubleDippers(limit, 0),
    enabled,
    placeholderData: keepPreviousData,
  });
  if (!enabled) return null;

  const add = (code: string) => {
    const result = query.data?.courses.find((c) => c.code === code);
    if (!result) return;
    const existing = courses.find((c) => c.code === code);
    const planCourse = existing ?? catalogToPlanCourse(result);
    const target = targetTerm(planCourse, existing ? courses : [...courses, planCourse], plan, profile);
    if (target.term) {
      onAdd(planCourse, target.term);
      setAdded(`${code} added to ${target.term}.`);
    } else {
      course.open(code);
    }
  };

  return (
    <div className="le-section" aria-labelledby="le-dd-h">
      <h3 className="le-h3 le-plain" id="le-dd-h">
        Courses that count twice
      </h3>
      <p className="muted le-summary">Each covers two or more of your remaining liberal education needs.</p>
      <p className="le-added" role="status" aria-live="polite">
        {added}
      </p>
      {query.isError ? (
        <p className="muted">
          Couldn't load suggestions.{" "}
          <Button size="sm" variant="ghost" onClick={() => query.refetch()}>
            Try again
          </Button>
        </p>
      ) : !query.data ? (
        <p className="muted">Loading suggestions…</p>
      ) : query.data.courses.length === 0 ? (
        <p className="muted">No single course covers two of your remaining needs.</p>
      ) : (
        <>
          <ul className="req-list">
            {query.data.courses.map((c) => (
              <li key={c.code} className="req-row">
                <span className="req-name">
                  <button type="button" className="le-course" onClick={() => course.open(c.code)}>
                    <b>{c.code}</b> {c.title}
                  </button>
                  <span className="muted">Counts for {c.covers.join(", ")}</span>
                </span>
                <Button size="sm" variant="quiet" onClick={() => add(c.code)} aria-label={`Add ${c.code} to plan`}>
                  <Plus className="ic sm" aria-hidden />
                  Add
                </Button>
              </li>
            ))}
          </ul>
          {query.data.total > query.data.courses.length && (
            <Button size="sm" variant="ghost" onClick={() => setLimit((n) => Math.min(50, n + 10))} disabled={query.isFetching}>
              Show more ({query.data.total - query.data.courses.length} more)
            </Button>
          )}
        </>
      )}
    </div>
  );
}

/** Liberal education status: diversified core, designated themes, writing, and courses that count twice. */
export function LiberalEdPanel({ plan, profile, courses, onAdd }: {
  plan: Plan;
  profile?: Profile;
  courses: Course[];
  onAdd: (course: Course, term: string) => void;
}) {
  const liberal = plan.liberalEd;
  if (!liberal) return null;
  const termOf = (code: string) => courses.find((c) => c.code === code)?.term ?? null;
  const { themes, writing } = liberal;
  const { intensive, firstYear } = writing;
  const rpj = themes.items.find((item) => themes.mandatory.includes(item.id));
  const writingStatus: LeSectionStatus =
    intensive.status === "met" && firstYear.status === "done" ? "met"
      : intensive.status === "short" || firstYear.status === "needed" ? "short" : "on_track";

  return (
    <section className="card surf le-panel" aria-labelledby="le-h">
      <h2 className="h2" id="le-h">
        Liberal education
      </h2>
      <p className="muted req-meta">
        From catalog designations{liberal.source === "catalog+apas" ? " and your APAS audit" : ""}. APAS has the final word.
      </p>

      <Section title="Diversified core" status={liberal.core.status} summary="One course in each of these 7 areas.">
        {liberal.core.items.map((item) => (
          <CategoryRow key={item.id} item={item} termOf={termOf} />
        ))}
      </Section>

      <Section
        title="Designated themes"
        status={themes.status}
        summary={`${themes.completed} of ${themes.required} done, ${themes.projected} with your plan.${rpj ? ` ${rpj.label} is required.` : ""}`}
      >
        {themes.items.map((item) => (
          <CategoryRow key={item.id} item={item} termOf={termOf} />
        ))}
      </Section>

      <Section title="Writing" status={writingStatus}>
        <li className="req-row">
          <span className="req-name">
            <b>{firstYear.label}</b>
            <span className="muted">
              {evidence(firstYear.codes, termOf) || `${firstYear.acceptedCodes.join(" or ")}, or an approved equivalent such as AP credit`}
            </span>
          </span>
          <Chip {...ITEM[firstYear.status]} />
        </li>
        <li className="req-row">
          <span className="req-name">
            <b>{intensive.label}</b>
            <span className="muted">
              {intensive.completed.total} of {intensive.required.total} done, {intensive.completed.upper} of {intensive.required.upper} upper division,{" "}
              {intensive.completed.upperInMajor} of {intensive.required.upperInMajor} upper division in your major.
              {intensive.projected.total > intensive.completed.total && ` ${intensive.projected.total} with your plan.`}
            </span>
            {evidence(intensive.codes, termOf) && <span className="muted">{evidence(intensive.codes, termOf)}</span>}
            {intensive.status === "short" && (
              <Link className="le-find" to={findLink("Writing Intensive")}>
                Find writing intensive courses
              </Link>
            )}
          </span>
          <Chip {...SECTION[intensive.status]} />
        </li>
      </Section>

      <DoubleDippers liberal={liberal} plan={plan} profile={profile} courses={courses} onAdd={onAdd} />
    </section>
  );
}
