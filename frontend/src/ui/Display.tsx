import type { ReactNode } from "react";
import { Link } from "react-router";
import { AlertTriangle, CalendarDays, Check, CheckCircle2, Clock, Info, Lock, Plus, XCircle } from "lucide-react";
import type { CourseStatus } from "@/api/types";
import { cn } from "@/lib/cn";

export const STATUS_LABEL: Record<CourseStatus, string> = {
  done: "Completed",
  prog: "In progress",
  plan: "Planned",
  avail: "Available",
  block: "Locked",
};
const STATUS_ICON = { done: Check, prog: Clock, plan: CalendarDays, avail: Plus, block: Lock };

/** Always icon plus text, so status never relies on color. */
export function StatusBadge({ status }: { status: CourseStatus }) {
  const Icon = STATUS_ICON[status];
  return (
    <span className={`badge b-${status}`}>
      <Icon className="ic" aria-hidden />
      {STATUS_LABEL[status]}
    </span>
  );
}

type Tone = "ok" | "warn" | "error" | "info";
const TONE_ICON = { ok: CheckCircle2, warn: AlertTriangle, error: XCircle, info: Info };

export function Callout({ tone, title, children }: { tone: Tone; title: ReactNode; children?: ReactNode }) {
  const Icon = TONE_ICON[tone];
  return (
    <div className={`callout ${tone}`} role={tone === "error" ? "alert" : undefined}>
      <Icon className="ic" aria-hidden />
      <div>
        <b>{title}</b>
        {children}
      </div>
    </div>
  );
}

export function ProgressBar({ label, value, max, over, className }: { label: string; value: number; max: number; over?: boolean; className?: string }) {
  const pct = max > 0 ? Math.min(100, (value / max) * 100) : 0;
  return (
    <div
      className={cn("bar", over && "over", className)}
      role="progressbar"
      aria-label={label}
      aria-valuenow={Math.min(value, max)}
      aria-valuemin={0}
      aria-valuemax={max}
    >
      <i style={{ width: `${pct}%` }} />
    </div>
  );
}

const R = 42;
const C = 2 * Math.PI * R;

/** Static ring. It reflects the value; it doesn't animate on load. */
export function ProgressRing({ percent, size = 128 }: { percent: number; size?: number }) {
  const p = Math.max(0, Math.min(100, Math.round(percent)));
  return (
    <svg className="ring" width={size} height={size} viewBox="0 0 100 100" role="img" aria-label={`${p} percent complete`}>
      <circle className="trk" cx="50" cy="50" r={R} />
      <circle className="arc" cx="50" cy="50" r={R} strokeDasharray={C} strokeDashoffset={C * (1 - p / 100)} transform="rotate(-90 50 50)" />
      <text x="50" y="51" className="num">
        {p}%
      </text>
    </svg>
  );
}

export const Spinner = () => <span className="spin" aria-hidden />;

/** Static placeholder rows. They hold the layout and do not pulse. */
export function SkeletonRows({ rows = 6 }: { rows?: number }) {
  return (
    <div className="surf" aria-busy="true" aria-label="Loading">
      {Array.from({ length: rows }, (_, i) => (
        <div className="skel" key={i}>
          <i style={{ width: "22%" }} />
          <i style={{ width: "38%" }} />
          <i style={{ width: "10%", marginLeft: "auto" }} />
        </div>
      ))}
    </div>
  );
}

export function EmptyState({ icon, title, children, action }: { icon?: ReactNode; title: string; children?: ReactNode; action?: ReactNode }) {
  return (
    <div className="surf empty">
      {icon}
      <h3>{title}</h3>
      {children && <p>{children}</p>}
      {action}
    </div>
  );
}

/** Preview-only controls for states the mock backend can't reach on its own. Hidden in production builds. */
export function DemoToggle({ children }: { children: ReactNode }) {
  if (!import.meta.env.DEV) return null;
  return <div className="demo">{children}</div>;
}

/** Step list for plan generation. Steps flip from pending to done; nothing slides or types. */
export function StepList({ steps, done }: { steps: string[]; done: number }) {
  return (
    <ol className="steps-list">
      {steps.map((s, i) => (
        <li key={s} className={cn("gstep", i < done && "done", i === done && "active")}>
          <span className="dot">{i < done ? <Check className="ic" aria-hidden /> : i === done ? <Spinner /> : null}</span>
          {s}
          <span className="vh">{i < done ? ", done" : i === done ? ", in progress" : ", waiting"}</span>
        </li>
      ))}
    </ol>
  );
}

export function Brand({ to = "/" }: { to?: string }) {
  return (
    <Link className="brand" to={to}>
      <img src="/favicon.png" alt="" />
      Gopher Planner
    </Link>
  );
}
