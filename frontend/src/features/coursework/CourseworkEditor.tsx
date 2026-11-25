import { useEffect, useId, useRef, useState } from "react";
import { useLeaveWarning } from "@/hooks/useLeaveWarning";
import { useAutosave } from "@/hooks/useAutosave";
import { keepPreviousData, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Plus, Trash2, Upload } from "lucide-react";
import { getCoursework, getCourses, getTranscript, saveCoursework, uploadTranscript } from "@/api/endpoints";
import { queryKeys } from "@/api/queryKeys";
import type { CourseworkEntry } from "@/api/types";
import { currentTerm } from "@/lib/terms";
import { Button, Callout, CourseRowsSkeleton, SaveToast, Select, SkeletonRegion, Spinner } from "@/ui";
import "./coursework.css";

const GRADES = ["A", "A-", "B+", "B", "B-", "C+", "C", "C-", "D+", "D", "F", "S", "N", "W", "I"];
const NO_GRADE = "No grade";
const UNKNOWN_TERM = "Term unknown";
const MAX_BYTES = 10 * 1024 * 1024;

/** Terms from five years back through next year, newest first. */
export function termOptions(today: Date = new Date()) {
  const year = today.getFullYear();
  const terms: string[] = [];
  for (let y = year + 1; y >= year - 5; y -= 1) terms.push(`Fall ${y}`, `Summer ${y}`, `Spring ${y}`);
  return terms;
}

const same = (a: CourseworkEntry[], b: CourseworkEntry[]) => JSON.stringify(a) === JSON.stringify(b);

/**
 * Saved coursework, editable after onboarding: change status, grade, term or credits, remove or add
 * courses, and re-upload an APAS PDF (imported rows are replaced; manual rows are kept).
 */
export function CourseworkEditor() {
  const qc = useQueryClient();
  const searchId = useId();
  const fileRef = useRef<HTMLInputElement>(null);
  const saved = useQuery({ queryKey: queryKeys.coursework, queryFn: getCoursework });
  const [rows, setRows] = useState<CourseworkEntry[]>([]);
  const [q, setQ] = useState("");
  const [message, setMessage] = useState<{ tone: "ok" | "warn" | "error"; title: string; body?: string } | null>(null);
  const [transcriptId, setTranscriptId] = useState("");
  const [uploading, setUploading] = useState(false);

  // Sync from the server only while the user has no unsaved edits, so a refetch can't wipe them.
  const editedRef = useRef(false);
  useEffect(() => {
    if (saved.data && !editedRef.current) setRows(saved.data.courses);
  }, [saved.data]);

  const search = useQuery({
    queryKey: queryKeys.courses({ q, limit: 5, offset: 0 }),
    queryFn: () => getCourses({ q, limit: 5, offset: 0 }),
    enabled: q.trim().length > 1,
    placeholderData: keepPreviousData,
  });

  const transcript = useQuery({
    queryKey: queryKeys.transcript(transcriptId),
    queryFn: () => getTranscript(transcriptId),
    enabled: !!transcriptId,
    refetchInterval: (query) => (query.state.data?.status === "parsing" ? 1000 : false),
  });

  useEffect(() => {
    const data = transcript.data;
    if (!data || data.status === "parsing") return;
    setTranscriptId("");
    if (data.status === "parsed") {
      editedRef.current = false;
      void qc.invalidateQueries({ queryKey: queryKeys.coursework });
      void qc.invalidateQueries({ queryKey: queryKeys.summary });
      void qc.invalidateQueries({ queryKey: queryKeys.plan });
      const skipped = data.notImported ?? [];
      setMessage({
        tone: "ok",
        title: `Imported ${data.completed} completed and ${data.inProgress} in-progress courses.`,
        body: skipped.length ? `Not imported (add by hand if they count): ${skipped.join(", ")}.` : undefined,
      });
    } else {
      setMessage({ tone: "warn", title: "We couldn't read any courses from that PDF.", body: "Your saved courses were not changed." });
    }
  }, [transcript.data, qc]);

  const save = useMutation({
    mutationFn: () => saveCoursework({ courses: rows, skipped: false }),
    onSuccess: (body) => {
      editedRef.current = false;
      setRows(body.courses);
      qc.setQueryData(queryKeys.coursework, body);
      void qc.invalidateQueries({ queryKey: queryKeys.summary });
      void qc.invalidateQueries({ queryKey: queryKeys.plan });
      setMessage(null);
    },
    onError: (error: Error) => setMessage({ tone: "error", title: "Could not save your courses.", body: error.message }),
  });

  const update = (index: number, patch: Partial<CourseworkEntry>) => {
    editedRef.current = true;
    setMessage(null);
    setRows((current) => current.map((row, i) => (i === index ? { ...row, ...patch } : row)));
  };

  const add = (code: string, title: string, credits: number) => {
    editedRef.current = true;
    setMessage(null);
    setRows((current) => [...current, { code, title, credits, status: "done", term: currentTerm(), grade: null, source: "manual" }]);
    setQ("");
  };

  const reupload = async (file: File) => {
    setMessage(null);
    if (file.size > MAX_BYTES) {
      setMessage({ tone: "error", title: "That PDF is over 10 MB." });
      return;
    }
    setUploading(true);
    try {
      const { id } = await uploadTranscript(file);
      setTranscriptId(id);
    } catch (error) {
      setMessage({ tone: "error", title: "The upload failed.", body: error instanceof Error ? error.message : undefined });
    } finally {
      setUploading(false);
    }
  };

  const reading = uploading || !!transcriptId;
  const dirty = !!saved.data && !same(rows, saved.data.courses);
  useLeaveWarning(dirty);
  // Course edits save on their own; uploads in progress hold the save until the file is read.
  useAutosave({ enabled: dirty && !reading && !save.isPending, key: JSON.stringify(rows), save: () => save.mutate(), failed: save.isError });
  const results = (search.data?.courses ?? []).filter((course) => !rows.some((row) => row.code === course.code));
  const terms = termOptions();

  return (
    <section className="sec surf" aria-labelledby="s-courses">
      <h2 id="s-courses">Your courses</h2>
      <p className="muted">Completed and in-progress courses the planner builds around.</p>

      <div className="cw-actions">
        <input
          ref={fileRef}
          type="file"
          accept="application/pdf,.pdf"
          hidden
          aria-label="APAS PDF"
          onChange={(event) => {
            const file = event.target.files?.[0];
            event.target.value = "";
            if (file) void reupload(file);
          }}
        />
        <Button variant="ghost" onClick={() => fileRef.current?.click()} disabled={reading}>
          {reading ? <Spinner /> : <Upload className="ic" aria-hidden />}
          {reading ? "Reading your PDF" : "Re-upload APAS PDF"}
        </Button>
        <span className="muted cw-note">Replaces imported courses. Courses you added by hand are kept.</span>
      </div>

      {message && (
        <Callout tone={message.tone} title={message.title}>
          {message.body}
        </Callout>
      )}

      {saved.isPending ? (
        <SkeletonRegion label="coursework"><CourseRowsSkeleton /></SkeletonRegion>
      ) : saved.isError ? (
        <Callout tone="error" title="Could not load your courses."><Button variant="ghost" onClick={() => saved.refetch()}>Try again</Button></Callout>
      ) : rows.length === 0 ? (
        <p className="muted">No courses saved yet. Search below or upload your APAS PDF.</p>
      ) : (
        <ul className="cw-list" aria-label="Saved courses">
          {rows.map((row, index) => (
            <li key={`${row.code}-${row.term ?? "unknown"}`} className="cw-row">
              <span className="cw-name">
                <b>{row.code}</b>
                <span className="muted">{row.title}</span>
              </span>
              <label className="cw-credits">
                <span className="sr-only">{row.code} credits</span>
                <input
                  className="input num"
                  inputMode="decimal"
                  defaultValue={row.credits}
                  key={row.credits}
                  onBlur={(event) => {
                    const n = Math.round(Number(event.target.value) * 2) / 2;
                    const credits = Number.isFinite(n) && n >= 0.5 ? Math.min(12, n) : row.credits;
                    event.target.value = String(credits);
                    if (credits !== row.credits) update(index, { credits });
                  }}
                />
              </label>
              <Select
                ariaLabel={`${row.code} status`}
                value={row.status === "prog" ? "In progress" : "Completed"}
                options={["Completed", "In progress"]}
                onChange={(value) => update(index, value === "In progress" ? { status: "prog", grade: null } : { status: "done" })}
              />
              <Select
                ariaLabel={`${row.code} grade`}
                value={row.grade ?? NO_GRADE}
                options={row.status === "prog" ? [NO_GRADE] : [NO_GRADE, ...GRADES]}
                onChange={(value) => update(index, { grade: value === NO_GRADE ? null : value })}
              />
              <Select
                ariaLabel={`${row.code} term`}
                value={row.term ?? UNKNOWN_TERM}
                options={[UNKNOWN_TERM, ...(row.term && !terms.includes(row.term) ? [row.term] : []), ...terms]}
                onChange={(value) => update(index, { term: value === UNKNOWN_TERM ? null : value })}
              />
              <Button
                variant="ghost"
                size="sm"
                aria-label={`Remove ${row.code}`}
                onClick={() => {
                  editedRef.current = true;
                  setMessage(null);
                  setRows((current) => current.filter((_, i) => i !== index));
                }}
              >
                <Trash2 className="ic" aria-hidden />
              </Button>
            </li>
          ))}
        </ul>
      )}

      <div className="field cw-search">
        <label className="label" htmlFor={searchId}>
          Add a course
        </label>
        <div className="inline-search">
          <input
            id={searchId}
            className="input"
            value={q}
            placeholder="Course code or title, for example CSCI 2041"
            onChange={(event) => setQ(event.target.value)}
          />
        </div>
        {q.trim().length > 1 && (
          <ul className="cw-list" aria-label="Course search results" aria-busy={search.isFetching}>
            {results.length ? (
              results.slice(0, 5).map((course) => (
                <li key={course.code} className="cw-row">
                  <span className="cw-name">
                    <b>{course.code}</b>
                    <span className="muted">{course.title}</span>
                  </span>
                  <Button variant="ghost" size="sm" onClick={() => add(course.code, course.title, course.minimumCredits || 1)}>
                    <Plus className="ic" aria-hidden />
                    Add {course.code}
                  </Button>
                </li>
              ))
            ) : (
              <li className="muted">{search.isFetching ? "Searching…" : "No matching courses."}</li>
            )}
          </ul>
        )}
      </div>

      <div className="cw-actions">
        <SaveToast saving={(dirty || save.isPending) && !save.isError} failed={save.isError} />
        {save.isError && dirty && <Button onClick={() => save.mutate()} disabled={save.isPending || reading}>Try again</Button>}
        {save.isError && dirty && (
          <Button variant="ghost" onClick={() => { editedRef.current = false; if (saved.data) setRows(saved.data.courses); }}>
            Undo changes
          </Button>
        )}
      </div>
    </section>
  );
}
