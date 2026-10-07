import { useEffect, useState } from "react";
import { useNavigate } from "react-router";
import { Search, X } from "lucide-react";
import { IconButton, StatusBadge } from "@/ui";
import { useCourseParam } from "@/features/course-detail/useCourseParam";
import { useCourseSearch } from "./useCourseSearch";

/** Mobile search: takes over the header bar, with results dropping down beneath it. */
export function HeaderSearch({ onClose }: { onClose: () => void }) {
  const [q, setQ] = useState("");
  const [active, setActive] = useState(0);
  const navigate = useNavigate();
  const course = useCourseParam();
  const { results, isFetching } = useCourseSearch(q, true);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && onClose();
    addEventListener("keydown", onKey);
    return () => removeEventListener("keydown", onKey);
  }, [onClose]);

  const pick = (code: string) => {
    onClose();
    course.open(code);
  };
  const toCatalog = () => {
    const query = q.trim();
    onClose();
    navigate(query ? `/catalog?q=${encodeURIComponent(query)}` : "/catalog");
  };

  return (
    <>
      <div className="hsearch-scrim" onClick={onClose} aria-hidden />
      <div className="hsearch" role="search">
        <Search className="ic muted" aria-hidden />
        <input
          autoFocus
          type="search"
          value={q}
          placeholder="Search courses or professors"
          aria-label="Search courses or professors"
          role="combobox"
          aria-expanded
          aria-controls="hsearch-results"
          aria-activedescendant={results[active] ? `hs-${active}` : undefined}
          onChange={(e) => {
            setQ(e.target.value);
            setActive(0);
          }}
          onKeyDown={(e) => {
            if (e.key === "ArrowDown") {
              e.preventDefault();
              setActive((a) => Math.min(a + 1, results.length - 1));
            } else if (e.key === "ArrowUp") {
              e.preventDefault();
              setActive((a) => Math.max(a - 1, 0));
            } else if (e.key === "Enter") {
              e.preventDefault();
              if (q.trim() && results[active]) pick(results[active].code);
              else toCatalog();
            }
          }}
        />
        <IconButton label="Close search" bare onClick={onClose}>
          <X className="ic" aria-hidden />
        </IconButton>
      </div>
      <div className="hsearch-res" id="hsearch-results" role="listbox" aria-busy={isFetching}>
        {results.length ? (
          results.map((c, i) => (
            <button key={c.code} id={`hs-${i}`} role="option" aria-selected={i === active} onClick={() => pick(c.code)}>
              <span className="t">
                <b>{c.code}</b>
                <span className="muted">{c.title}</span>
              </span>
              <StatusBadge status={c.status} />
            </button>
          ))
        ) : (
          <p className="muted hsearch-empty">{isFetching ? "Searching…" : "No matches. Try a broader course code, such as CSCI."}</p>
        )}
        <button className="hsearch-all" onClick={toCatalog}>
          Open the full catalog
        </button>
      </div>
    </>
  );
}
