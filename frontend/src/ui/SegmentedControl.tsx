import { useRef } from "react";
import type { KeyboardEvent, ReactNode } from "react";
import { cn } from "@/lib/cn";

export interface SegOption<T extends string> {
  value: T;
  label: ReactNode;
  icon?: ReactNode;
}

interface Props<T extends string> {
  label: string;
  value: T;
  onChange: (value: T) => void;
  options: SegOption<T>[];
  className?: string;
}

/** Radio group styled as a pill switch. Arrow keys move and select. */
export function SegmentedControl<T extends string>({ label, value, onChange, options, className }: Props<T>) {
  const ref = useRef<HTMLDivElement>(null);
  const onKey = (e: KeyboardEvent) => {
    const dir = e.key === "ArrowRight" || e.key === "ArrowDown" ? 1 : e.key === "ArrowLeft" || e.key === "ArrowUp" ? -1 : 0;
    if (!dir) return;
    e.preventDefault();
    const i = options.findIndex((o) => o.value === value);
    const next = options[(i + dir + options.length) % options.length];
    onChange(next.value);
    ref.current?.querySelector<HTMLButtonElement>(`[data-v="${next.value}"]`)?.focus();
  };
  return (
    <div ref={ref} className={cn("seg", className)} role="radiogroup" aria-label={label} onKeyDown={onKey}>
      {options.map((o) => (
        <button
          key={o.value}
          type="button"
          role="radio"
          data-v={o.value}
          aria-checked={o.value === value}
          tabIndex={o.value === value ? 0 : -1}
          onClick={() => onChange(o.value)}
        >
          {o.icon}
          {o.label}
        </button>
      ))}
    </div>
  );
}
