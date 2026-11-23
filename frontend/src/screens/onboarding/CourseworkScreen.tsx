import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { queryKeys } from "@/api/queryKeys";
import { getCoursework, getTranscript, saveCoursework } from "@/api/endpoints";
import type { Coursework } from "@/api/types";
import { currentTerm } from "@/lib/terms";
import { Button, Callout } from "@/ui";
import { StepHeader } from "./components/StepHeader";
import { ImportChoice } from "./components/ImportChoice";
import { ApasUploader } from "./components/ApasUploader";
import { ManualEntry } from "./components/ManualEntry";
import { toCourseworkEntries } from "./coursework";
import { useOnboarding } from "./onboarding.store";
import "./onboarding.css";

export default function CourseworkScreen() {
  const navigate = useNavigate();
  const qc = useQueryClient();
  const { method, setMethod, upload, manual, setManual } = useOnboarding();
  const [error, setError] = useState("");
  const id = upload?.transcriptId ?? "";

  // The parent owns the transcript query so the step can decide whether Continue is allowed.
  const transcript = useQuery({
    queryKey: queryKeys.transcript(id),
    queryFn: () => getTranscript(id),
    enabled: !!id,
    refetchInterval: (q) => (q.state.data?.status === "parsing" ? 1000 : false),
  });
  const saved = useQuery({ queryKey: queryKeys.coursework, queryFn: getCoursework });

  // Restore manual entries after a refresh: the server is the source of truth, the store a draft.
  const restored = useRef(false);
  useEffect(() => {
    if (restored.current || !saved.data) return;
    restored.current = true;
    const rows = saved.data.courses.filter((course) => course.source !== "transcript");
    if (!manual.length && !upload && rows.length) {
      setManual(rows.map((course) => ({ code: course.code, title: course.title, credits: course.credits, status: course.status })));
      setMethod("manual");
    }
  }, [saved.data, manual.length, upload, setManual, setMethod]);

  const save = useMutation({
    mutationFn: (body: Coursework) => saveCoursework(body),
    onSuccess: (body) => {
      qc.setQueryData(queryKeys.coursework, body);
      navigate("/onboarding/profile");
    },
    onError: (failure: Error) => setError(`We couldn't save your coursework. ${failure.message}`),
  });

  const status = transcript.data?.status;
  const busy = save.isPending || (method === "upload" && !!upload && (!transcript.data || status === "parsing"));

  const onContinue = () => {
    setError("");
    if (method === "upload") {
      if (status !== "parsed") {
        setError(upload ? "Your PDF couldn't be read. Enter your courses manually, or upload a different file." : "Upload your APAS PDF, or choose another option.");
        return;
      }
      navigate("/onboarding/profile");
      return;
    }
    if (method === "manual") {
      if (manual.length === 0) {
        setError("Add at least one course, or choose Skip for now.");
        return;
      }
      const transcriptRows = (saved.data?.courses ?? []).filter((course) => course.source === "transcript"
        && !manual.some((entry) => entry.code === course.code));
      save.mutate({ courses: [...transcriptRows, ...toCourseworkEntries(manual, currentTerm())], skipped: false });
      return;
    }
    save.mutate({ courses: [], skipped: true });
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

      {method === "upload" && (
        <ApasUploader transcript={transcript.data} transcriptError={transcript.error} onManual={() => setMethod("manual")} />
      )}
      {method === "manual" && <ManualEntry />}
      {method === "skip" && (
        <div className="panel surf">
          <Callout tone="info" title="Standard four-year plan">
            We build it from your major's requirements. You can add coursework any time from Settings.
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
          {save.isPending ? "Saving" : "Continue"}
        </Button>
      </div>
    </>
  );
}
