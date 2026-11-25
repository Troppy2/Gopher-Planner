import { useEffect, useRef, useState } from "react";
import { CheckCircle2 } from "lucide-react";

/**
 * Bottom toast for autosaving forms: "Saving…" while `saving`, then a brief "Saved" once it ends
 * without a failure. Failures are left to the caller, which owns the retry and undo actions.
 */
export function SaveToast({ saving, failed = false }: { saving: boolean; failed?: boolean }) {
  const [justSaved, setJustSaved] = useState(false);
  const wasSaving = useRef(saving);

  useEffect(() => {
    const finished = wasSaving.current && !saving && !failed;
    wasSaving.current = saving;
    if (!finished) return;
    setJustSaved(true);
    const timer = window.setTimeout(() => setJustSaved(false), 1600);
    return () => window.clearTimeout(timer);
  }, [saving, failed]);

  if (failed) return null;
  if (saving) {
    return <div className="savebar" role="status"><span className="msg">Saving…</span></div>;
  }
  if (!justSaved) return null;
  return (
    <div className="savebar" role="status">
      <span className="msg">
        <CheckCircle2 className="ic" style={{ color: "var(--success)" }} aria-hidden />
        <b>Saved</b>
      </span>
    </div>
  );
}
