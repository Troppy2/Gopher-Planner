import { useEffect, useRef, useState } from "react";
import { CheckCircle2 } from "lucide-react";
import { Button } from "@/ui";
import { plural } from "@/lib/format";
import { violationText } from "@/lib/violations";
import { useAutosave } from "@/hooks/useAutosave";
import { useLeaveWarning } from "@/hooks/useLeaveWarning";
import { usePlan } from "./usePlan";

/**
 * Plan edits save themselves shortly after the user stops editing, including when they move to
 * another page (this stays mounted app-wide; `visible` only controls the bar). A generated plan
 * replaces the whole plan, so it waits for "Keep this plan" instead.
 */
export function UnsavedPlanBar({ visible = true }: { visible?: boolean }) {
  const { pendingCount, versionPending, isBuildDraft, draftKey, violations, save, saveState, discard } = usePlan();
  const [justSaved, setJustSaved] = useState(false);
  const [confirmDiscard, setConfirmDiscard] = useState(false);
  const timer = useRef<number>(0);

  useEffect(() => () => clearTimeout(timer.current), []);

  const pending = pendingCount > 0 || versionPending;
  const failed = saveState.isError;
  useLeaveWarning(pending);

  const onSave = async () => {
    const result = await save();
    if (!result) return;
    setJustSaved(true);
    clearTimeout(timer.current);
    timer.current = window.setTimeout(() => setJustSaved(false), 1600);
  };

  useAutosave({ enabled: pending && !isBuildDraft && !saveState.isPending, key: draftKey, save: () => void onSave(), failed });

  if (!visible) return null;
  if (saveState.isPending || (pending && !isBuildDraft && !failed)) {
    return <div className="savebar" role="status"><span className="msg">Saving…</span></div>;
  }
  if (!pending && justSaved && !failed) {
    return (
      <div className="savebar" role="status">
        <span className="msg">
          <CheckCircle2 className="ic" style={{ color: "var(--success)" }} aria-hidden />
          <b>Saved</b>
        </span>
      </div>
    );
  }
  if (!pending) return null;

  return (
    <div className="savebar" role={failed ? "alert" : "status"}>
      <div className="msg">
        <b>{failed ? "Couldn't save your plan." : isBuildDraft ? "New plan draft" : plural(pendingCount, "unsaved change")}</b>
        {failed && violations.length > 0 && (
          <ul className="violations">
            {violations.map((violation) => (
              <li key={`${violation.code}-${violation.reason}`}>{violationText(violation)}</li>
            ))}
          </ul>
        )}
        {failed && !violations.length && saveState.error && <span>{saveState.error.message}</span>}
      </div>
      {confirmDiscard ? <>
        <Button variant="ghost" size="sm" onClick={() => setConfirmDiscard(false)}>Keep</Button>
        <Button variant="ghost" size="sm" className="danger-text" onClick={() => { setConfirmDiscard(false); discard(); }}>
          Discard {pendingCount > 1 ? `all ${pendingCount}` : ""}
        </Button>
      </> : <Button variant="ghost" size="sm" onClick={() => pendingCount > 1 ? setConfirmDiscard(true) : discard()}>
        Discard
      </Button>}
      <Button size="sm" onClick={onSave}>
        {failed ? "Try again" : "Keep this plan"}
      </Button>
    </div>
  );
}
