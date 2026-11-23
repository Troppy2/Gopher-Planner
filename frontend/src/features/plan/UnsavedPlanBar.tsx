import { useEffect, useRef, useState } from "react";
import { CheckCircle2 } from "lucide-react";
import { Button } from "@/ui";
import { plural } from "@/lib/format";
import { violationText } from "@/lib/violations";
import { usePlan } from "./usePlan";

export function UnsavedPlanBar() {
  const { pendingCount, versionPending, violations, save, saveState, discard } = usePlan();
  const [justSaved, setJustSaved] = useState(false);
  const timer = useRef<number>(0);

  useEffect(() => () => clearTimeout(timer.current), []);

  const onSave = () => {
    void save();
    setJustSaved(true);
    clearTimeout(timer.current);
    timer.current = window.setTimeout(() => setJustSaved(false), 1600);
  };

  const pending = pendingCount > 0 || versionPending;
  if (!pending && justSaved && !saveState.isError) {
    return (
      <div className="savebar" role="status">
        <span className="msg">
          <CheckCircle2 className="ic" style={{ color: "var(--success)" }} aria-hidden />
          <b>Plan saved</b>
        </span>
      </div>
    );
  }
  if (!pending) return null;

  const failed = saveState.isError;
  return (
    <div className="savebar" role="status">
      <span className="msg">
        <b>{failed ? "Could not save." : pendingCount ? plural(pendingCount, "unsaved change") : "Catalog year not saved"}</b>
        {failed && violations.length > 0 && (
          <ul className="violations">
            {violations.map((violation) => (
              <li key={`${violation.code}-${violation.reason}`}>{violationText(violation)}</li>
            ))}
          </ul>
        )}
        {failed && !violations.length && saveState.error && <span>{saveState.error.message}</span>}
      </span>
      <Button variant="ghost" size="sm" onClick={discard}>
        Discard
      </Button>
      <Button size="sm" onClick={onSave}>
        {failed ? "Try again" : "Save plan"}
      </Button>
    </div>
  );
}
