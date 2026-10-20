import { useQuery } from "@tanstack/react-query";
import { ExternalLink, Plus, RefreshCw } from "lucide-react";
import { getCatalogCourse } from "@/api/endpoints";
import type { CatalogCourse, Course } from "@/api/types";
import { Button, Callout, Drawer, StatusBadge } from "@/ui";
import { usePlan } from "@/features/plan/usePlan";
import { targetTerm } from "@/features/plan/planRules";
import { PrerequisiteTree } from "./PrerequisiteTree";
import { useCourseParam } from "./useCourseParam";
import "./course-detail.css";

function formatCredits(course: CatalogCourse): string {
  if (course.minimumCredits === course.maximumCredits) {
    return String(course.minimumCredits);
  }

  return `${course.minimumCredits}–${course.maximumCredits}`;
}

function formatValue(value: string | null | undefined): string {
  if (!value || value.trim() === "" || value.trim() === "-") {
    return "Not specified";
  }

  return value;
}

function getPlanStatus(planCourse: Course | undefined): Course["status"] {
  return planCourse?.status ?? "avail";
}

export function CourseDrawer() {
  const { code, close } = useCourseParam();
  const { courses, plan, profile, add, remove } = usePlan();

  const details = useQuery({
    queryKey: ["catalog-course", code],
    queryFn: () => getCatalogCourse(code!),
    enabled: Boolean(code),
  });

  if (!code) return null;

  const catalogCourse = details.data;
  const planCourse = courses.find((course) => course.code === code);
  const status = getPlanStatus(planCourse);

  const target =
    plan && planCourse?.status === "avail"
      ? targetTerm(planCourse, courses, plan, profile)
      : null;

  let note = null;
  let action = null;

  if (planCourse?.status === "block") {
    note = (
      <Callout tone="warn" title="Locked for you right now">
        {planCourse.lockReason ||
          "This course is currently locked in your plan."}
      </Callout>
    );
  } else if (target?.term && planCourse) {
    note = (
      <Callout tone="ok" title={`Prerequisites are met by ${target.term}`}>
        Adding puts it in {target.term}. Nothing is saved until you press Save
        plan.
      </Callout>
    );

    const term = target.term;

    action = (
      <Button
        onClick={() => {
          add(code, term);
          close();
        }}
      >
        <Plus className="ic sm" aria-hidden />
        Add to {term}
      </Button>
    );
  } else if (target && planCourse) {
    note = target.missing.length ? (
      <Callout tone="warn" title="Prerequisite conflict">
        {target.missing.join(", ")} {target.missing.length > 1 ? "are" : "is"}{" "}
        not in your plan yet. Add {target.missing.length > 1 ? "them" : "it"}{" "}
        first.
      </Callout>
    ) : (
      <Callout tone="info" title="No open term">
        It isn't offered in a term before your graduation target.
      </Callout>
    );

    action = <Button disabled>Add to plan</Button>;
  } else if (planCourse?.status === "plan") {
    action = (
      <Button
        variant="ghost"
        onClick={() => {
          remove(code);
          close();
        }}
      >
        Remove from plan
      </Button>
    );
  } else if (!planCourse) {
    note = (
      <Callout tone="info" title="Catalog course">
        This course is in the catalog but is not yet connected to your plan. You
        can review its details below.
      </Callout>
    );
  }

  const prerequisiteData = catalogCourse?.prerequisites;
  const prerequisiteExpression = prerequisiteData?.requirements;
  const prerequisiteSource =
    prerequisiteData?.source_text ||
    catalogCourse?.prerequisiteSourceText ||
    "";
  const prerequisiteStatus =
    prerequisiteData?.status || catalogCourse?.prerequisiteStatus || "";

  const hasPrerequisiteSource =
    prerequisiteSource.trim() !== "" && prerequisiteSource.trim() !== "-";

  const hasNoPrerequisites =
    prerequisiteStatus.toLowerCase() === "none" &&
    !prerequisiteExpression &&
    !hasPrerequisiteSource;

  return (
    <Drawer
      open
      onOpenChange={(open) => !open && close()}
      title={catalogCourse?.code ?? code}
      subtitle={catalogCourse?.title ?? "Course details"}
      closeLabel="Close details"
      footer={
        <>
          {action}
          <Button variant="ghost" onClick={close}>
            Close
          </Button>
        </>
      }
    >
      {details.isPending && (
        <div className="detail-loading" role="status">
          <RefreshCw className="ic sm" aria-hidden />
          Loading course details…
        </div>
      )}

      {details.isError && (
        <EmptyCourseDetails onRetry={() => void details.refetch()} />
      )}

      {catalogCourse && (
        <>
          <div className="detail-status">
            <StatusBadge status={status} />
            {catalogCourse.campus && (
              <span className="muted">{catalogCourse.campus}</span>
            )}
          </div>

          {note}

          <dl className="facts">
            <div>
              <dt>Credits</dt>
              <dd className="num">{formatCredits(catalogCourse)}</dd>
            </div>
            <div>
              <dt>Typically offered</dt>
              <dd>{formatValue(catalogCourse.typicallyOffered)}</dd>
            </div>
            <div>
              <dt>Grading basis</dt>
              <dd>{formatValue(catalogCourse.gradingBasis)}</dd>
            </div>
            <div>
              <dt>Repeatable</dt>
              <dd>{formatValue(catalogCourse.repeatable)}</dd>
            </div>
            {planCourse && (
              <div>
                <dt>Planned term</dt>
                <dd>{planCourse.term ?? "Not placed"}</dd>
              </div>
            )}
          </dl>

          <section>
            <h3 className="dsub">Course description</h3>
            {catalogCourse.description.trim() &&
            catalogCourse.description.trim() !== "-" ? (
              <p className="course-description">{catalogCourse.description}</p>
            ) : (
              <p className="muted">No description available.</p>
            )}
          </section>

          <section>
            <h3 className="dsub">Prerequisites</h3>

            {hasNoPrerequisites ? (
              <p className="muted">No prerequisites listed in the catalog.</p>
            ) : prerequisiteExpression ? (
              <>
                {prerequisiteData?.needs_review && (
                  <Callout tone="warn" title="Prerequisites need review">
                    The extracted prerequisite structure may need verification.
                    Check the original catalog text before relying on it.
                  </Callout>
                )}

                <PrerequisiteTree expression={prerequisiteExpression} />

                <p className="muted prerequisite-status">
                  Prerequisite data status: {formatValue(prerequisiteStatus)}
                </p>
              </>
            ) : (
              <>
                <p className="muted">
                  Structured prerequisite requirements are not available for
                  this course.
                </p>

                <p className="muted prerequisite-status">
                  Prerequisite data status: {formatValue(prerequisiteStatus)}
                </p>
              </>
            )}

            {hasPrerequisiteSource && (
              <div className="prerequisite-source">
                <h4>Original catalog text</h4>
                <p>{prerequisiteSource}</p>
              </div>
            )}
          </section>

          <div className="dlinks">
            <a
              className="btn ghost sm"
              href="https://umn.lol"
              target="_blank"
              rel="noopener noreferrer"
            >
              Gopher Grades
              <ExternalLink className="ic sm" aria-hidden />
            </a>
          </div>
        </>
      )}
    </Drawer>
  );
}

function EmptyCourseDetails({ onRetry }: { onRetry: () => void }) {
  return (
    <Callout tone="warn" title="Couldn't load course details">
      <p>We couldn't retrieve this course from the catalog.</p>
      <Button variant="ghost" onClick={onRetry}>
        <RefreshCw className="ic sm" aria-hidden />
        Try again
      </Button>
    </Callout>
  );
}
