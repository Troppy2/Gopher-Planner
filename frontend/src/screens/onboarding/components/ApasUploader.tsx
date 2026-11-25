import { useState } from "react";
import { FileText } from "lucide-react";
import { uploadTranscript } from "@/api/endpoints";
import type { Transcript } from "@/api/types";
import { Button, Callout, Dropzone, Spinner } from "@/ui";
import { useOnboarding } from "../onboarding.store";
import { toManualCourse } from "../coursework";

const MAX_BYTES = 10 * 1024 * 1024;
const sizeLabel = (b: number) => (b > 1024 * 1024 ? `${(b / 1024 / 1024).toFixed(1)} MB` : `${Math.max(1, Math.round(b / 1024))} KB`);

interface Props {
  transcript: Transcript | undefined;
  transcriptError: Error | null;
  onManual: () => void;
}

export function ApasUploader({ transcript, transcriptError, onManual }: Props) {
  const { upload, setUpload, setManual } = useOnboarding();
  // A rejected file and a failed upload need different titles: only the first is the student's file.
  const [fileError, setFileError] = useState<{ title: string; detail: string } | null>(null);

  const start = async (file: File) => {
    setFileError(null);
    if (file.type && file.type !== "application/pdf" && !file.name.toLowerCase().endsWith(".pdf")) {
      setFileError({ title: "Couldn't use that file", detail: "That file isn't a PDF. Export your APAS report as a PDF and try again." });
      return;
    }
    if (file.size > MAX_BYTES) {
      setFileError({ title: "Couldn't use that file", detail: "That PDF is over 10 MB. Try exporting only the APAS report pages." });
      return;
    }
    setUpload({ fileName: file.name, sizeLabel: sizeLabel(file.size), transcriptId: null });
    try {
      const { id } = await uploadTranscript(file);
      useOnboarding.setState((s) => (s.upload ? { upload: { ...s.upload, transcriptId: id } } : s));
    } catch (error) {
      setUpload(null);
      setFileError({ title: "The upload didn't finish", detail: error instanceof Error ? error.message : "Try again." });
    }
  };

  const correct = () => {
    setManual((transcript?.courses ?? []).map(toManualCourse));
    onManual();
  };

  const uploading = !!upload && !upload.transcriptId;
  const status = transcript?.status;
  const settled = status === "parsed" || status === "no_text" || status === "failed";

  return (
    <div className="panel surf">
      {!upload ? (
        <Dropzone title="Drop your APAS PDF here" hint="PDF only, up to 10 MB. Exported and scanned PDFs both work." accept="application/pdf,.pdf" onFile={start} />
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
                <>
                  <Spinner />
                  Uploading and reading
                </>
              ) : status === "parsed" ? (
                "Read"
              ) : status === "no_text" ? (
                "No text found"
              ) : status === "failed" ? (
                "Could not read"
              ) : transcriptError ? (
                "Status unavailable"
              ) : (
                <>
                  <Spinner />
                  Reading your courses
                </>
              )}
            </span>
          </div>
        </div>
      )}

      {uploading && (
        <p className="muted">Scanned pages can take up to a minute while we recognize the text.</p>
      )}

      {fileError && <Callout tone="error" title={fileError.title}>{fileError.detail}</Callout>}
      {transcriptError && <Callout tone="error" title="We couldn't check your upload.">{transcriptError.message}</Callout>}

      {status === "parsed" && transcript && (
        <div className="stack">
          <Callout tone="ok" title={`We found ${transcript.completed} completed and ${transcript.inProgress} in-progress courses.`}>
            Check them below. Correct anything that looks wrong before you continue.
          </Callout>
          {(transcript.notImported?.length ?? 0) > 0 && (
            <Callout
              tone="warn"
              title={`${transcript.notImported!.length} ${transcript.notImported!.length === 1 ? "course" : "courses"} couldn't be imported.`}
            >
              Transfer placeholders and codes we couldn't read: {transcript.notImported!.join(", ")}. Add them by hand if
              they count toward your degree.
            </Callout>
          )}
          <ul className="mlist" aria-label="Courses found in your PDF">
            {(transcript.courses ?? []).map((course) => (
              <li key={`${course.code}-${course.term ?? "unknown"}`} className="mrow">
                <span className="mrow-t">
                  <b>{course.code}</b>
                  <span className="muted">{course.title}</span>
                </span>
                <span className="muted num">
                  {course.credits} cr, {course.status === "prog" ? "In progress" : course.grade ?? "No grade"}, {course.term ?? "Term unknown"}
                </span>
              </li>
            ))}
          </ul>
          <div>
            <Button variant="ghost" onClick={correct}>Correct these courses</Button>
          </div>
        </div>
      )}

      {status === "no_text" && (
        <div className="stack">
          <Callout tone="warn" title="We couldn't read any text in this PDF.">
            We tried, even with text recognition for scans. Upload a clearer scan, or add your courses by
            hand. Nothing you uploaded is kept.
          </Callout>
          <div className="row">
            <Button onClick={onManual}>Enter courses manually</Button>
          </div>
        </div>
      )}

      {status === "failed" && (
        <div className="stack">
          <Callout tone="error" title="We couldn't find any courses in this PDF.">
            {transcript?.errorCode === "unreadable_pdf"
              ? "The file couldn't be opened as a PDF."
              : "The layout wasn't recognized. Enter your courses manually, or upload a different APAS PDF."}
          </Callout>
          <div className="row">
            <Button onClick={onManual}>Enter courses manually</Button>
          </div>
        </div>
      )}

      {upload && !uploading && settled && (
        <div>
          <Button variant="quiet" size="sm" onClick={() => setUpload(null)}>
            Upload a different file
          </Button>
        </div>
      )}
    </div>
  );
}
