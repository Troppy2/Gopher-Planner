import { useState } from "react";
import { useSearchParams } from "react-router";
import { keepPreviousData, useQuery } from "@tanstack/react-query";
import {
  AlertTriangle,
  ChevronLeft,
  ChevronRight,
  RefreshCw,
  SlidersHorizontal,
  X,
} from "lucide-react";
import { getCourses } from "@/api/endpoints";
import { queryKeys } from "@/api/queryKeys";
import type { CourseFilters } from "@/api/types";
import { Button, Drawer, EmptyState } from "@/ui";
import { CatalogSkeleton } from "@/features/loading/ScreenSkeletons";
import { plural } from "@/lib/format";
import { usePlan } from "@/features/plan/usePlan";
import { useCourseParam } from "@/features/course-detail/useCourseParam";
import { catalogToPlanCourse, targetTerm } from "@/features/plan/planRules";
import { FilterFields, FILTERS } from "./components/FilterFields";
import type { FilterKey } from "./components/FilterFields";
import { ResultsList } from "./components/ResultsList";
import "./catalog.css";

type Filters = Record<FilterKey, string>;

const PAGE_SIZE = 25;

const EMPTY: Filters = {
  subject: "",
  level: "",
  credits: "",
  term: "",
  availability: "",
};

export default function CatalogScreen() {
  const [params, setParams] = useSearchParams();
  const q = params.get("q") ?? "";
  // Liberal education designation, set by links such as the dashboard's "Find courses".
  const le = params.get("le") ?? "";

  const [filters, setFilters] = useState<Filters>(EMPTY);
  const [page, setPage] = useState(0);
  const [sheetOpen, setSheetOpen] = useState(false);
  const [live, setLive] = useState("");

  const course = useCourseParam();
  const { courses: planCourses, plan, profile, add, addCourse } = usePlan();

  const query: CourseFilters = {
    q,
    ...filters,
    ...(le ? { le } : {}),
    limit: PAGE_SIZE,
    offset: page * PAGE_SIZE,
  };

  const results = useQuery({
    queryKey: queryKeys.courses(query),
    queryFn: () => getCourses(query),
    placeholderData: keepPreviousData,
  });

  const setQ = (value: string) => {
    const nextParams = new URLSearchParams(params);

    if (value) {
      nextParams.set("q", value);
    } else {
      nextParams.delete("q");
    }

    setPage(0);
    setParams(nextParams, { replace: true });
  };

  const updateFilter = (key: FilterKey, value: string) => {
    setFilters((previous) => ({
      ...previous,
      [key]: value,
    }));
    setPage(0);
  };

  const clearLe = () => {
    const nextParams = new URLSearchParams(params);
    nextParams.delete("le");
    setPage(0);
    setParams(nextParams, { replace: true });
  };

  const clearAll = () => {
    setFilters(EMPTY);
    setPage(0);
    const nextParams = new URLSearchParams(params);
    nextParams.delete("q");
    nextParams.delete("le");
    setParams(nextParams, { replace: true });
  };

  const active = (Object.keys(filters) as FilterKey[]).filter(
    (key) => filters[key] !== "",
  );

  const catalogCourses = results.data?.courses ?? [];

  const list = catalogCourses.map((catalogCourse) => ({
    ...catalogCourse,
    planCourse: planCourses.find(
      (planCourse) => planCourse.code === catalogCourse.code,
    ),
  }));

  const total = results.data?.total ?? 0;
  const pageCount = Math.ceil(total / PAGE_SIZE);
  const startResult = total === 0 ? 0 : page * PAGE_SIZE + 1;
  const endResult = Math.min((page + 1) * PAGE_SIZE, total);

  const onAdd = (code: string) => {
    if (!plan) {
      setLive("Create or load a plan before adding courses.");
      return;
    }

    const existing = planCourses.find(
      (planCourse) => planCourse.code === code,
    );
    const result = catalogCourses.find((catalogCourse) => catalogCourse.code === code);
    // Catalog courses outside the plan are added as electives; the server validates on save.
    const planCourse = existing ?? (result ? catalogToPlanCourse(result) : undefined);

    if (!planCourse || planCourse.status === "block") {
      if (planCourse?.lockReason) setLive(`${code}: ${planCourse.lockReason}`);
      course.open(code);
      return;
    }

    const target = targetTerm(planCourse, [...planCourses, ...(existing ? [] : [planCourse])], plan, profile);

    if (target.term) {
      if (existing) add(code, target.term);
      else addCourse(planCourse, target.term);
      setLive(`${code} added to ${target.term}. Save your plan to keep it.`);
    } else {
      course.open(code);
    }
  };

  let body;

  if (results.isError) {
    body = (
      <EmptyState
        icon={
          <AlertTriangle
            className="ic"
            style={{ color: "var(--warning)" }}
            aria-hidden
          />
        }
        title="We couldn't load the catalog"
        action={
          <Button onClick={() => results.refetch()}>
            <RefreshCw className="ic sm" aria-hidden />
            Try again
          </Button>
        }
      >
        The course data didn't come back. Check your connection and try again.
      </EmptyState>
    );
  } else if (!results.data) {
    body = <CatalogSkeleton />;
  } else if (list.length === 0) {
    body = (
      <EmptyState
        title="No courses match"
        action={
          <Button variant="ghost" onClick={clearAll}>
            Clear filters and search
          </Button>
        }
      >
        Try a broader course code, such as CSCI, or clear a filter.
      </EmptyState>
    );
  } else {
    body = <ResultsList courses={list} onOpen={course.open} onAdd={onAdd} />;
  }

  return (
    <div className="page">
      <div className="pg-head">
        <h1 className="title">Course catalog</h1>
      </div>

      <label className="searchbar surf">
        <span className="vh">Search courses</span>
        <input
          type="search"
          value={q}
          placeholder="Search course codes, titles, or descriptions"
          onChange={(event) => setQ(event.target.value)}
        />
      </label>

      <div className="filters">
        <FilterFields values={filters} onChange={updateFilter} />
      </div>

      <div className="cat-tools">
        <Button
          variant="ghost"
          size="sm"
          className="fbtn"
          onClick={() => setSheetOpen(true)}
        >
          <SlidersHorizontal className="ic sm" aria-hidden />
          Filters{active.length + (le ? 1 : 0) ? ` (${active.length + (le ? 1 : 0)})` : ""}
        </Button>
      </div>

      <div className="summary" aria-live="polite">
        {results.data && !results.isError && (
          <>
            <span className="num">
              {plural(total, "course")}
              {results.isFetching && <span className="muted"> (updating)</span>}
            </span>

            {total > 0 && (
              <span className="muted">
                · Showing {startResult}–{endResult}
              </span>
            )}
          </>
        )}

        {le && (
          <button className="chip" onClick={clearLe} aria-label={`Remove filter Liberal ed: ${le}`}>
            Liberal ed: {le}
            <X className="ic sm" aria-hidden />
          </button>
        )}

        {active.map((key) => {
          const label =
            FILTERS.find((filter) => filter.key === key)?.label ?? (key === "subject" ? "Subject" : key);

          return (
            <button
              key={key}
              className="chip"
              onClick={() => updateFilter(key, "")}
              aria-label={`Remove filter ${label}: ${filters[key]}`}
            >
              {label}: {filters[key]}
              <X className="ic sm" aria-hidden />
            </button>
          );
        })}
      </div>

      <p className="vh" role="status" aria-live="polite">
        {live}
      </p>

      {body}

      {results.data && total > PAGE_SIZE && !results.isError && (
        <nav className="catalog-pagination" aria-label="Course catalog pages">
          <Button
            variant="ghost"
            disabled={page === 0 || results.isFetching}
            onClick={() => {
              setPage((current) => Math.max(0, current - 1));
              window.scrollTo({ top: 0, behavior: "smooth" });
            }}
            aria-label="Go to previous page"
          >
            <ChevronLeft className="ic sm" aria-hidden />
            Previous
          </Button>

          <span className="catalog-page-indicator" aria-live="polite">
            Page {page + 1} of {pageCount}
          </span>

          <Button
            variant="ghost"
            disabled={page >= pageCount - 1 || results.isFetching}
            onClick={() => {
              setPage((current) => Math.min(pageCount - 1, current + 1));
              window.scrollTo({ top: 0, behavior: "smooth" });
            }}
            aria-label="Go to next page"
          >
            Next
            <ChevronRight className="ic sm" aria-hidden />
          </Button>
        </nav>
      )}

      <Drawer
        open={sheetOpen}
        onOpenChange={setSheetOpen}
        title="Filters"
        closeLabel="Close filters"
        footer={
          <>
            <Button
              variant="ghost"
              onClick={() => {
                setFilters(EMPTY);
                setPage(0);
              }}
            >
              Clear all
            </Button>
            <Button style={{ flex: 1 }} onClick={() => setSheetOpen(false)}>
              Show {results.data ? plural(total, "result") : "results"}
            </Button>
          </>
        }
      >
        <FilterFields values={filters} onChange={updateFilter} />
      </Drawer>
    </div>
  );
}
