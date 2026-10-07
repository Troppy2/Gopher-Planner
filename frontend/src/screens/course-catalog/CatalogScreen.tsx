import { useState } from "react";
import { useSearchParams } from "react-router";
import { keepPreviousData, useQuery } from "@tanstack/react-query";
import { AlertTriangle, RefreshCw, Search, SlidersHorizontal, X } from "lucide-react";
import { getCourses } from "@/api/endpoints";
import { mockFlags } from "@/api/mock/mockDb";
import { queryKeys } from "@/api/queryKeys";
import type { CourseFilters } from "@/api/types";
import { Button, Checkbox, DemoToggle, Drawer, EmptyState, SkeletonRows } from "@/ui";
import { plural } from "@/lib/format";
import { usePlan } from "@/features/plan/usePlan";
import { useCourseParam } from "@/features/course-detail/useCourseParam";
import { targetTerm } from "@/features/plan/planRules";
import { FilterFields, FILTERS } from "./components/FilterFields";
import type { FilterKey } from "./components/FilterFields";
import { ResultsList } from "./components/ResultsList";
import "./catalog.css";

type Filters = Record<FilterKey, string>;
const EMPTY: Filters = { subject: "", level: "", credits: "", term: "", requirement: "", availability: "" };

export default function CatalogScreen() {
  const [params, setParams] = useSearchParams();
  const q = params.get("q") ?? "";
  const [filters, setFilters] = useState<Filters>(EMPTY);
  const [sheetOpen, setSheetOpen] = useState(false);
  const [failPreview, setFailPreview] = useState(mockFlags.failCatalog);
  const [live, setLive] = useState("");
  const course = useCourseParam();
  const { courses: planCourses, plan, profile, add } = usePlan();

  const query: CourseFilters = { q, ...filters };
  const results = useQuery({
    queryKey: queryKeys.courses(query),
    queryFn: () => getCourses(query),
    placeholderData: keepPreviousData,
  });

  const setQ = (v: string) => {
    const p = new URLSearchParams(params);
    if (v) p.set("q", v);
    else p.delete("q");
    setParams(p, { replace: true });
  };
  const clearAll = () => {
    setFilters(EMPTY);
    setQ("");
  };
  const active = (Object.keys(filters) as FilterKey[]).filter((k) => filters[k]);

  // Overlay unsaved plan edits so status matches the rest of the app.
  const list = (results.data ?? []).map((c) => planCourses.find((x) => x.code === c.code) ?? c);

  const onAdd = (code: string) => {
    const c = list.find((x) => x.code === code);
    if (!c || !plan) return;
    const t = targetTerm(c, planCourses, plan, profile);
    if (t.term) {
      add(code, t.term);
      setLive(`${code} added to ${t.term}. Save your plan to keep it.`);
    } else {
      course.open(code); // shows why it can't be added
    }
  };

  let body;
  if (results.isError) {
    body = (
      <EmptyState
        icon={<AlertTriangle className="ic" style={{ color: "var(--warning)" }} aria-hidden />}
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
    body = <SkeletonRows rows={6} />;
  } else if (!list.length) {
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
        <Search className="ic muted" aria-hidden />
        <span className="vh">Search courses</span>
        <input type="search" value={q} placeholder="Search courses or professors" onChange={(e) => setQ(e.target.value)} />
      </label>

      <div className="filters">
        <FilterFields values={filters} onChange={(k, v) => setFilters({ ...filters, [k]: v })} />
      </div>

      <div className="cat-tools">
        <Button variant="ghost" size="sm" className="fbtn" onClick={() => setSheetOpen(true)}>
          <SlidersHorizontal className="ic sm" aria-hidden />
          Filters{active.length ? ` (${active.length})` : ""}
        </Button>
        <DemoToggle>
          <Checkbox
            checked={failPreview}
            onChange={(v) => {
              setFailPreview(v);
              mockFlags.failCatalog = v;
              results.refetch();
            }}
          >
            Preview only: catalog fails to load
          </Checkbox>
        </DemoToggle>
      </div>

      <div className="summary" aria-live="polite">
        {results.data && !results.isError && (
          <span className="num">
            {plural(list.length, "course")}
            {results.isFetching && <span className="muted"> (updating)</span>}
          </span>
        )}
        {active.map((k) => {
          const label = FILTERS.find((f) => f.key === k)!.label;
          return (
            <button key={k} className="chip" onClick={() => setFilters({ ...filters, [k]: "" })} aria-label={`Remove filter ${label}: ${filters[k]}`}>
              {label}: {filters[k]}
              <X className="ic sm" aria-hidden />
            </button>
          );
        })}
      </div>
      <p className="vh" role="status" aria-live="polite">
        {live}
      </p>

      {body}

      <Drawer
        open={sheetOpen}
        onOpenChange={setSheetOpen}
        title="Filters"
        closeLabel="Close filters"
        footer={
          <>
            <Button variant="ghost" onClick={() => setFilters(EMPTY)}>
              Clear all
            </Button>
            <Button style={{ flex: 1 }} onClick={() => setSheetOpen(false)}>
              Show {results.data ? plural(list.length, "result") : "results"}
            </Button>
          </>
        }
      >
        <FilterFields values={filters} onChange={(k, v) => setFilters({ ...filters, [k]: v })} />
      </Drawer>
    </div>
  );
}
