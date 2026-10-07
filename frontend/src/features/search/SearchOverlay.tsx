import { useState } from "react";
import * as Dialog from "@radix-ui/react-dialog";
import { useNavigate } from "react-router";
import { Search, X } from "lucide-react";
import { Button, IconButton, StatusBadge } from "@/ui";
import { useCourseParam } from "@/features/course-detail/useCourseParam";
import { useCourseSearch } from "./useCourseSearch";

interface Props {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function SearchOverlay({ open, onOpenChange }: Props) {
  const [q, setQ] = useState("");
  const [active, setActive] = useState(0);
  const navigate = useNavigate();
  const course = useCourseParam();
  const { results, isFetching } = useCourseSearch(q, open);

  const close = () => {
    setQ("");
    setActive(0);
    onOpenChange(false);
  };
  const toCatalog = () => {
    const query = q.trim();
    close();
    navigate(query ? `/catalog?q=${encodeURIComponent(query)}` : "/catalog");
  };
  const pick = (code: string) => {
    close();
    course.open(code);
  };

  return (
    <Dialog.Root
      open={open}
      onOpenChange={(o) => (o ? onOpenChange(true) : close())}
    >
      <Dialog.Portal>
        <Dialog.Overlay className="searchov" />
        <Dialog.Content className="sbox" aria-describedby={undefined}>
          <Dialog.Title className="vh">Search courses</Dialog.Title>
          <div className="top">
            <Search className="ic muted" aria-hidden />
            <input
              autoFocus
              value={q}
              placeholder="Search courses, professors, or course codes"
              aria-label="Search"
              role="combobox"
              aria-expanded
              aria-controls="search-results"
              aria-activedescendant={results[active] ? `sr-${active}` : undefined}
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
            <Dialog.Close asChild>
              <IconButton label="Close search" bare>
                <X className="ic" aria-hidden />
              </IconButton>
            </Dialog.Close>
          </div>
          <div className="res" id="search-results" role="listbox" aria-busy={isFetching}>
            {results.length ? (
              results.map((c, i) => (
                <button
                  key={c.code}
                  id={`sr-${i}`}
                  role="option"
                  aria-selected={i === active}
                  onMouseEnter={() => setActive(i)}
                  onClick={() => pick(c.code)}
                >
                  <span className="t">
                    <b>{c.code}</b> <span className="muted">{c.title}</span>
                  </span>
                  <StatusBadge status={c.status} />
                </button>
              ))
            ) : (
              <p className="muted" style={{ padding: 14 }}>
                {isFetching ? "Searching…" : "No matches. Try a broader course code, such as CSCI."}
              </p>
            )}
          </div>
          <div className="foot">
            <span>Enter opens the selected course</span>
            <Button variant="ghost" size="sm" onClick={toCatalog}>
              Open catalog
            </Button>
          </div>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}
