import type { WarningCode } from "@/api/types";
import { translateWarning } from "@/lib/warnings";

/** Shown elsewhere already: the elective-credit note and each requirement's "Needs review" chip. */
const SHOWN_ELSEWHERE = new Set<WarningCode>(["graduation_target_unreachable", "requirements_need_review", "requirements_incomplete"]);

/** Plan-wide caveats, collapsed by default so they don't crowd out the student's actual progress. */
export function PlanWarnings({ warnings }: { warnings: WarningCode[] }) {
  const shown = warnings.filter((code) => !SHOWN_ELSEWHERE.has(code));
  if (!shown.length) return null;
  return (
    <details className="warn-box">
      <summary className="warn-title">
        {shown.length === 1 ? "1 thing to check before registering" : `${shown.length} things to check before registering`}
      </summary>
      <ul className="warn-list">
        {shown.map((code) => (
          <li key={code}>{translateWarning(code)}</li>
        ))}
      </ul>
    </details>
  );
}
