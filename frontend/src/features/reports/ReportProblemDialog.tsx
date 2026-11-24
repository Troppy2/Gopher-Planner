import { useId, useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { createReport } from "@/api/endpoints";
import { ApiError } from "@/api/client";
import { queryKeys } from "@/api/queryKeys";
import type { DataReport, NewReport, ReportReason } from "@/api/types";
import { Button, Callout, Spinner, TextArea } from "@/ui";
import { usePlanDraft } from "@/features/plan/plan.store";
import { REPORT_REASONS } from "./reasons";
import type { ReportTarget } from "./reasons";
import "./reports.css";

export function ReportProblemDialog({ target, existing, onClose }: { target: ReportTarget; existing?: DataReport; onClose: () => void }) {
  const [reason, setReason] = useState<ReportReason | "">(existing?.reason ?? "");
  const [note, setNote] = useState(existing?.note ?? "");
  const name = useId();
  const qc = useQueryClient();
  const send = useMutation({
    mutationFn: createReport,
    onSuccess: (report) => {
      qc.setQueryData<{ reports: DataReport[] }>(queryKeys.reports, previous => ({
        reports: [report, ...(previous?.reports ?? []).filter(r => r.id !== report.id)],
      }));
      void qc.invalidateQueries({ queryKey: queryKeys.reports });
      usePlanDraft.getState().announce("Thanks. We'll review your report.");
      onClose();
    },
  });
  return <form className="report-form" onSubmit={e => {
    e.preventDefault();
    if (!reason || send.isPending) return;
    const body: NewReport = target.type === "course"
      ? { targetType: "course", courseCode: target.courseCode, reason, note }
      : { targetType: "requirement", requirementId: target.requirementId, reason, note };
    send.mutate(body);
  }}>
    <fieldset disabled={send.isPending}><legend>What is the problem?</legend>
      {REPORT_REASONS[target.type].map(option => <label className="report-reason" key={option.code}>
        <input type="radio" name={name} value={option.code} checked={reason === option.code} onChange={() => setReason(option.code)} />
        <span>{option.label}</span>
      </label>)}
    </fieldset>
    <TextArea label="What's wrong? (optional)" value={note} onChange={e => setNote(e.target.value)} maxLength={500} rows={4} disabled={send.isPending}
      hint="Don't include personal details like your student ID or grades." />
    <p className="muted report-count" aria-live="polite">{Array.from(note).length}/500 characters</p>
    {send.isError && <Callout tone="error" title={send.error instanceof ApiError && send.error.status === 429
      ? "You've sent a lot of reports today. Try again tomorrow."
      : "Couldn't send your report. Check your connection and try again."} />}
    <div className="report-actions">
      <Button variant="ghost" onClick={onClose}>Cancel</Button>
      <Button type="submit" disabled={!reason || send.isPending}>{send.isPending && <Spinner />}Send report</Button>
    </div>
  </form>;
}
