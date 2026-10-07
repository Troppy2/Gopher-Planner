import { useEffect, useState } from "react";
import { Link } from "react-router";
import { useQueryClient } from "@tanstack/react-query";
import { generatePlan, updateProfile } from "@/api/endpoints";
import { queryKeys } from "@/api/queryKeys";
import { Button, Callout, ProgressBar, StepList } from "@/ui";
import { useReducedMotion } from "@/hooks/useMediaQuery";
import { useOnboarding } from "./onboarding.store";
import "./onboarding.css";

const STEPS = ["Reading your coursework", "Checking prerequisites and restrictions", "Placing courses by term", "Balancing your credit load"];

export default function BuildingPlanScreen() {
  const qc = useQueryClient();
  const reduced = useReducedMotion();
  const reset = useOnboarding((s) => s.reset);
  const [done, setDone] = useState(0);
  const [failed, setFailed] = useState(false);
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    let cancelled = false;
    const timers: number[] = [];
    setDone(0);
    setFailed(false);
    generatePlan()
      .then(() => {
        const gap = reduced ? 150 : 700;
        STEPS.forEach((_, i) =>
          timers.push(
            window.setTimeout(async () => {
              if (cancelled) return;
              setDone(i + 1);
              if (i === STEPS.length - 1) {
                try {
                  const p = await updateProfile({ onboarded: true });
                  qc.setQueryData(queryKeys.profile, p);
                  reset();
                } catch {
                  if (!cancelled) setFailed(true);
                }
              }
            }, gap * (i + 1)),
          ),
        );
      })
      .catch(() => !cancelled && setFailed(true));
    return () => {
      cancelled = true;
      timers.forEach(clearTimeout);
    };
  }, [attempt, reduced, qc, reset]);

  const ready = done === STEPS.length && !failed;

  return (
    <>
      <h1 className="title" style={{ marginTop: 32 }}>
        {ready ? "Your plan is ready" : "Building your plan"}
      </h1>
      <p className="sub" role="status">
        {ready ? "Review it on your dashboard." : "This takes a few seconds."}
      </p>
      <div className="gen surf">
        <ProgressBar label="Plan progress" value={done} max={STEPS.length} />
        <StepList steps={STEPS} done={done} />
      </div>
      {failed && (
        <div style={{ marginBottom: 16 }}>
          <Callout tone="error" title="We couldn't build your plan.">
            Your profile and coursework are saved. Try again.
          </Callout>
        </div>
      )}
      <div className="actions">
        <span />
        {failed ? (
          <Button onClick={() => setAttempt((a) => a + 1)}>Try again</Button>
        ) : ready ? (
          <Link className="btn" to="/dashboard">
            Go to dashboard
          </Link>
        ) : null}
      </div>
    </>
  );
}
