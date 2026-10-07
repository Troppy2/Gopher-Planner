import { useId, useState } from "react";
import { keepPreviousData, useQuery } from "@tanstack/react-query";
import { Plus, Search, X } from "lucide-react";
import { getCourses } from "@/api/endpoints";
import { queryKeys } from "@/api/queryKeys";
import { Button, IconButton, SegmentedControl } from "@/ui";
import { useOnboarding } from "../onboarding.store";

export function ManualEntry() {
  const id = useId();
  const [q, setQ] = useState("");
  const { manual, addManual, setManualStatus, removeManual } = useOnboarding();
  const { data = [], isFetching } = useQuery({
    queryKey: queryKeys.courses({ q }),
    queryFn: () => getCourses({ q }),
    enabled: q.trim().length > 1,
    placeholderData: keepPreviousData,
  });
  const results = q.trim().length > 1 ? data.filter((c) => !manual.some((m) => m.code === c.code)).slice(0, 5) : [];

  return (
    <div className="panel surf">
      <div className="field">
        <label className="label" htmlFor={id}>
          Search courses
        </label>
        <div className="inline-search">
          <Search className="ic muted" aria-hidden />
          <input id={id} className="input" value={q} placeholder="Course code or title, for example CSCI 2041" onChange={(e) => setQ(e.target.value)} />
        </div>
      </div>

      {q.trim().length > 1 && (
        <ul className="mlist" aria-label="Search results" aria-busy={isFetching}>
          {results.length ? (
            results.map((c) => (
              <li key={c.code} className="mrow">
                <span className="mrow-t">
                  <b>{c.code}</b>
                  <span className="muted">{c.title}</span>
                </span>
                <Button variant="ghost" size="sm" onClick={() => addManual({ code: c.code, title: c.title, status: "done" })} aria-label={`Add ${c.code}`}>
                  <Plus className="ic sm" aria-hidden />
                  Add
                </Button>
              </li>
            ))
          ) : (
            <li className="muted mrow">{isFetching ? "Searching…" : "No matches. Try a course code such as CSCI."}</li>
          )}
        </ul>
      )}

      <div>
        <h2 className="h2" style={{ marginBottom: 4 }}>
          Your courses <span className="muted num">({manual.length})</span>
        </h2>
        {manual.length ? (
          <ul className="mlist">
            {manual.map((m) => (
              <li key={m.code} className="mrow">
                <span className="mrow-t">
                  <b>{m.code}</b>
                  <span className="muted">{m.title}</span>
                </span>
                <span className="row">
                  <SegmentedControl
                    label={`${m.code} status`}
                    value={m.status}
                    onChange={(v) => setManualStatus(m.code, v)}
                    options={[
                      { value: "done", label: "Completed" },
                      { value: "prog", label: "In progress" },
                    ]}
                  />
                  <IconButton label={`Remove ${m.code}`} bare onClick={() => removeManual(m.code)}>
                    <X className="ic" aria-hidden />
                  </IconButton>
                </span>
              </li>
            ))}
          </ul>
        ) : (
          <p className="muted">Courses you add show up here.</p>
        )}
      </div>
    </div>
  );
}
