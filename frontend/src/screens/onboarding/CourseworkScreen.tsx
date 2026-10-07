import { useState } from "react";
import { useNavigate } from "react-router";
import { useQuery } from "@tanstack/react-query";
import { queryKeys } from "@/api/queryKeys";
import { getTranscript } from "@/api/endpoints";
import { Button, Callout } from "@/ui";
import { StepHeader } from "./components/StepHeader";
import { ImportChoice } from "./components/ImportChoice";
import { ApasUploader } from "./components/ApasUploader";
import { ManualEntry } from "./components/ManualEntry";
import { useOnboarding } from "./onboarding.store";
import "./onboarding.css";

export default function CourseworkScreen() {
  const navigate = useNavigate();
  const { method, setMethod, upload, manual } = useOnboarding();
  const [error, setError] = useState("");
  const id = upload?.transcriptId ?? "";
  const { data: transcript } = useQuery({ queryKey: queryKeys.transcript(id), queryFn: () => getTranscript(id), enabled: false });

  const busy = method === "upload" && !!upload && (upload.progress < 100 || !transcript || transcript.status === "parsing");

  const onContinue = () => {
    if (method === "upload" && transcript?.status !== "parsed") {
      setError(upload ? "Your PDF couldn't be read. Try text recognition, or enter your courses manually." : "Upload your APAS PDF, or choose another option.");
      return;
    }
    if (method === "manual" && manual.length === 0) {
      setError("Add at least one course, or choose Skip for now.");
      return;
    }
    navigate("/onboarding/profile");
  };

  return (
    <>
      <StepHeader step={1} total={2} />
      <h1 className="title">Add your coursework</h1>
      <ImportChoice
        value={method}
        onChange={(m) => {
          setMethod(m);
          setError("");
        }}
      />

      {method === "upload" && <ApasUploader onManual={() => setMethod("manual")} />}
      {method === "manual" && <ManualEntry />}
      {method === "skip" && (
        <div className="panel surf">
          <Callout tone="info" title="Standard four-year plan">
            We build it from your major and career goals. You can add coursework any time from Settings.
          </Callout>
        </div>
      )}

      {error && (
        <div style={{ marginBottom: 16 }}>
          <Callout tone="warn" title={error} />
        </div>
      )}

      <div className="actions">
        <span />
        <Button onClick={onContinue} disabled={busy}>
          Continue
        </Button>
      </div>
    </>
  );
}
