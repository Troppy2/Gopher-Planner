import { useCallback, useEffect, useId, useState } from "react";
import { Link } from "react-router";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { generatePlan, getPlan, updateProfile } from "@/api/endpoints";
import { queryKeys } from "@/api/queryKeys";
import type { GenerateResult, TermId } from "@/api/types";
import { translateWarning } from "@/lib/warnings";
import { Button, Callout, ProgressBar, StepList } from "@/ui";
import { useOnboarding } from "./onboarding.store";
import "./onboarding.css";

const STEPS = ["Reading your coursework", "Confirming your catalog year", "Placing courses by term", "Saving your plan"];
const VERSION_WARNINGS = ["program_version_unconfirmed", "program_version_unavailable"];

export default function BuildingPlanScreen() {
  const qc = useQueryClient();
  const reset = useOnboarding((s) => s.reset);
  const name = useId();
  const plan = useQuery({ queryKey: queryKeys.plan, queryFn: getPlan });
  const [selected, setSelected] = useState<TermId | null>(null);
  const [confirmed, setConfirmed] = useState<TermId | null | undefined>(undefined);
  const [result, setResult] = useState<GenerateResult | null>(null);
  const [failed, setFailed] = useState(false);
  const [finished, setFinished] = useState(false);
  const [running, setRunning] = useState(false);

  // A known program needs an explicit catalog year; unknown majors continue without one.
  const needsChoice = !!plan.data && !plan.data.catalogTerm && plan.data.availableCatalogTerms.length > 0;
  useEffect(() => {
    if (plan.data && confirmed === undefined && !needsChoice) setConfirmed(plan.data.catalogTerm);
  }, [plan.data, confirmed, needsChoice]);

  const run = useCallback(async (term: TermId | null) => {
    setRunning(true);
    setFailed(false);
    setResult(null);
    try {
      const generated = await generatePlan({ catalogTerm: term });
      setResult(generated);
      qc.setQueryData(queryKeys.plan, generated.plan);
      if (!generated.warnings.some((code) => VERSION_WARNINGS.includes(code))) {
        // Only a confirmed (or unknown) program completes onboarding.
        const profile = await updateProfile({ onboarded: true });
        qc.setQueryData(queryKeys.profile, profile);
        reset();
        setFinished(true);
      }
    } catch {
      setFailed(true);
    } finally {
      setRunning(false);
    }
  }, [qc, reset]);

  useEffect(() => {
    if (confirmed !== undefined && !result && !failed && !running && !finished) void run(confirmed);
  }, [confirmed, result, failed, running, finished, run]);

  const versionProblem = result?.warnings.some((code) => VERSION_WARNINGS.includes(code));
  const done = finished ? 4 : result ? 3 : confirmed !== undefined ? 2 : plan.data ? 1 : 0;
  const warnings = (result?.warnings ?? []).filter((code) => !VERSION_WARNINGS.includes(code));

  return (
    <>
      <h1 className="title" style={{ marginTop: 32 }}>
        {finished ? "Your plan is ready" : "Building your plan"}
      </h1>
      <p className="sub" role="status">
        {finished ? "Review it on your dashboard." : needsChoice && confirmed === undefined ? "One choice before we start." : "This takes a few seconds."}
      </p>
      <div className="gen surf">
        <ProgressBar label="Plan progress" value={done} max={STEPS.length} />
        <StepList steps={STEPS} done={done} />
      </div>

      {plan.error && (
        <Callout tone="error" title="We couldn't load your plan.">{plan.error.message}</Callout>
      )}

      {((needsChoice && confirmed === undefined) || versionProblem) && plan.data && (
        <fieldset className="panel surf">
          <legend className="h2">Choose the catalog year you follow</legend>
          <p className="muted">
            Requirements change between catalog years. Pick the year on your APAS report, usually the term you started your major.
          </p>
          {plan.data.availableCatalogTerms.map((term) => (
            <label key={term} className="row">
              <input type="radio" name={name} value={term} checked={selected === term} onChange={() => setSelected(term)} />
              {term}
            </label>
          ))}
          <div>
            <Button
              disabled={!selected || running}
              onClick={() => {
                // Clearing the result lets the effect generate with the newly confirmed year exactly once.
                setResult(null);
                setConfirmed(selected);
              }}
            >
              Build my plan
            </Button>
          </div>
        </fieldset>
      )}

      {warnings.length > 0 && (
        <div className="stack" style={{ marginBottom: 16 }}>
          {warnings.map((code) => (
            <Callout key={code} tone="info" title={translateWarning(code)} />
          ))}
        </div>
      )}

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
          <Button onClick={() => void run(confirmed ?? null)}>Try again</Button>
        ) : finished ? (
          <Link className="btn" to="/dashboard">
            Go to dashboard
          </Link>
        ) : null}
      </div>
    </>
  );
}
