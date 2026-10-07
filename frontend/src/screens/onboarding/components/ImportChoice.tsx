import { useRef } from "react";
import type { KeyboardEvent } from "react";
import { Check, PenLine, SkipForward, Upload } from "lucide-react";
import type { ImportMethod } from "../onboarding.store";

const OPTIONS = [
  { value: "upload", Icon: Upload, title: "Upload APAS", desc: "Upload your APAS or transcript PDF and we read the courses for you." },
  { value: "manual", Icon: PenLine, title: "Enter courses manually", desc: "Search the catalog and mark each course completed or in progress." },
  { value: "skip", Icon: SkipForward, title: "Skip for now", desc: "No classes yet? We start with a standard four-year plan for your major." },
] as const;

export function ImportChoice({ value, onChange }: { value: ImportMethod; onChange: (v: ImportMethod) => void }) {
  const ref = useRef<HTMLDivElement>(null);
  const onKey = (e: KeyboardEvent) => {
    const dir = e.key === "ArrowDown" || e.key === "ArrowRight" ? 1 : e.key === "ArrowUp" || e.key === "ArrowLeft" ? -1 : 0;
    if (!dir) return;
    e.preventDefault();
    const i = OPTIONS.findIndex((o) => o.value === value);
    const next = OPTIONS[(i + dir + OPTIONS.length) % OPTIONS.length].value;
    onChange(next);
    ref.current?.querySelector<HTMLButtonElement>(`[data-v="${next}"]`)?.focus();
  };
  return (
    <div ref={ref} className="opts" role="radiogroup" aria-label="How do you want to add coursework?" onKeyDown={onKey}>
      {OPTIONS.map(({ value: v, Icon, title, desc }) => (
        <button
          key={v}
          type="button"
          role="radio"
          data-v={v}
          className="opt"
          aria-checked={v === value}
          tabIndex={v === value ? 0 : -1}
          onClick={() => onChange(v)}
        >
          <span className="oi">
            <Icon className="ic" aria-hidden />
          </span>
          <span>
            <b>{title}</b>
            <span className="d">{desc}</span>
          </span>
          <span className="tick">
            <Check className="ic" aria-hidden />
          </span>
        </button>
      ))}
    </div>
  );
}
