import { useEffect, useRef, useState } from "react";
import { CheckCircle2 } from "lucide-react";
import { Button } from "@/ui";
import { plural } from "@/lib/format";
import { usePlan } from "./usePlan";

export function UnsavedPlanBar() {
  const { pendingCount, save, saveState, discard } = usePlan();
  const [justSaved, setJustSaved] = useState(false);
  const timer = useRef<number>(0);

  useEffect(() => () => clearTimeout(timer.current), []);

  const onSave = () => {
    save();
    setJustSaved(true);
    clearTimeout(timer.current);
    timer.current = window.setTimeout(() => setJustSaved(false), 1600);
  };

  if (pendingCount === 0 && justSaved && !saveState.isError) {
    return (
      <div className="savebar" role="status">
        <span className="msg">
          <CheckCircle2 className="ic" style={{ color: "var(--success)" }} aria-hidden />
          <b>Plan saved</b>
        </span>
      </div>
    );
  }
  if (pendingCount === 0) return null;

  return (
    <div className="savebar" role="status">
      <span className="msg">
        <b>{saveState.isError ? "Could not save. Try again." : plural(pendingCount, "unsaved change")}</b>
      </span>
      <Button variant="ghost" size="sm" onClick={discard}>
        Discard
      </Button>
      <Button size="sm" onClick={onSave}>
        {saveState.isError ? "Try again" : "Save plan"}
      </Button>
    </div>
  );
}
