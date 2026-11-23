import type { ReactNode } from "react";
import { ProgressBar, ProgressRing } from "@/ui";
import { useIsMobile } from "@/hooks/useMediaQuery";

interface Props {
  className: string;
  label: string;
  value: ReactNode;
  total?: number;
  bar?: { value: number; max: number };
  children?: ReactNode;
}

/** Label first, value second, context third. */
export function MetricCard({ className, label, value, total, bar, children }: Props) {
  return (
    <section className={`card surf metric ${className}`}>
      <h2 className="lab">{label}</h2>
      <div className="val num">
        {value}
        {total != null && <small> / {total}</small>}
      </div>
      {bar && <ProgressBar className="metric-bar" label={`${label} completed`} value={bar.value} max={bar.max} />}
      <p className="ctx">{children}</p>
    </section>
  );
}

export function PercentCard({ className, percent, total, source }: { className: string; percent: number | null; total: number | null; source: string }) {
  const mobile = useIsMobile();
  return (
    <section className={`card surf metric pct ${className}`}>
      {percent != null ? <ProgressRing percent={percent} size={mobile ? 96 : 128} /> : <div className="ring-na">N/A</div>}
      <div>
        <h2 className="lab">Credit progress</h2>
        <p className="pct-prog">{percent != null && total ? `${percent}% of ${total} degree credits` : "N/A"}</p>
        <p className="ctx">
          {percent != null ? `${source}. Counts credits only, not requirements.` : "Add your coursework to see this."}
        </p>
      </div>
    </section>
  );
}
