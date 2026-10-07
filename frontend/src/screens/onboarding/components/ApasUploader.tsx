import { useEffect, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { FileText } from "lucide-react";
import { getTranscript, retryTranscriptOcr, uploadTranscript } from "@/api/endpoints";
import { mockFlags } from "@/api/mock/mockDb";
import { queryKeys } from "@/api/queryKeys";
import { Button, Callout, DemoToggle, Dropzone, ProgressBar, SegmentedControl, Spinner } from "@/ui";
import { useOnboarding } from "../onboarding.store";

const MAX_BYTES = 10 * 1024 * 1024;
const sizeLabel = (b: number) => (b > 1024 * 1024 ? `${(b / 1024 / 1024).toFixed(1)} MB` : `${Math.max(1, Math.round(b / 1024))} KB`);

export function ApasUploader({ onManual }: { onManual: () => void }) {
  const { upload, setUpload } = useOnboarding();
  const [fileError, setFileError] = useState("");
  const [outcome, setOutcome] = useState<"ok" | "scan">(mockFlags.nextUploadIsScan ? "scan" : "ok");

  const id = upload?.transcriptId ?? null;
  const transcript = useQuery({
    queryKey: queryKeys.transcript(id ?? ""),
    queryFn: () => getTranscript(id!),
    enabled: !!id,
    refetchInterval: (q) => (q.state.data?.status === "parsing" || !q.state.data ? 1000 : false),
  });

  // Simulated byte upload; the real version reads XHR upload progress.
  const uploading = !!upload && upload.progress < 100;
  useEffect(() => {
    if (!upload || upload.progress >= 100) return;
    const t = setTimeout(() => setUpload({ ...upload, progress: Math.min(100, upload.progress + 14) }), 120);
    return () => clearTimeout(t);
  }, [upload, setUpload]);

  const start = async (file: File) => {
    setFileError("");
    if (file.type && file.type !== "application/pdf" && !file.name.toLowerCase().endsWith(".pdf")) {
      setFileError("That file isn't a PDF. Export your APAS report as a PDF and try again.");
      return;
    }
    if (file.size > MAX_BYTES) {
      setFileError("That PDF is over 10 MB. Try exporting only the APAS report pages.");
      return;
    }
    setUpload({ fileName: file.name, sizeLabel: sizeLabel(file.size), progress: 0, transcriptId: null });
    const { id } = await uploadTranscript(file);
    useOnboarding.setState((s) => (s.upload ? { upload: { ...s.upload, transcriptId: id } } : s));
  };

  const status = transcript.data?.status;

  return (
    <div className="panel surf">
      {!upload ? (
        <>
          <Dropzone title="Drop your APAS PDF here" hint="PDF only, up to 10 MB. Text-based PDFs work best." accept="application/pdf,.pdf" onFile={start} />
          {fileError && <Callout tone="error" title="Couldn't use that file">{fileError}</Callout>}
        </>
      ) : (
        <div className="upfile">
          <div className="upfile-row">
            <span className="upfile-name">
              <FileText className="ic" aria-hidden />
              <b>{upload.fileName}</b>
              <span className="muted num">{upload.sizeLabel}</span>
            </span>
            <span className="muted upfile-state" role="status">
              {uploading ? (
                "Uploading"
              ) : status === "parsed" ? (
                "Read"
              ) : status === "no_text" ? (
                "No text found"
              ) : (
                <>
                  <Spinner />
                  Reading your courses
                </>
              )}
            </span>
          </div>
          <ProgressBar label="Upload progress" value={upload.progress} max={100} />
        </div>
      )}

      {status === "parsed" && transcript.data && (
        <Callout tone="ok" title={`We found ${transcript.data.completed} completed and ${transcript.data.inProgress} in-progress courses.`}>
          You can check them on your dashboard once your plan is built.
        </Callout>
      )}

      {status === "no_text" && (
        <div className="stack">
          <Callout tone="warn" title="We couldn't read any text in this PDF.">
            It looks like a scan or photo. Try text recognition (OCR), or add your courses by hand.
          </Callout>
          <div className="row">
            <Button
              onClick={async () => {
                await retryTranscriptOcr(id!);
                transcript.refetch();
              }}
            >
              Try text recognition
            </Button>
            <Button variant="ghost" onClick={onManual}>
              Enter courses manually
            </Button>
          </div>
        </div>
      )}

      {upload && !uploading && (status === "parsed" || status === "no_text") && (
        <div>
          <Button variant="quiet" size="sm" onClick={() => setUpload(null)}>
            Upload a different file
          </Button>
        </div>
      )}

      <DemoToggle>
        Preview only. Outcome of the next upload:
        <SegmentedControl
          label="Upload outcome"
          value={outcome}
          onChange={(v) => {
            setOutcome(v);
            mockFlags.nextUploadIsScan = v === "scan";
          }}
          options={[
            { value: "ok", label: "Readable PDF" },
            { value: "scan", label: "Scanned PDF" },
          ]}
        />
      </DemoToggle>
    </div>
  );
}
