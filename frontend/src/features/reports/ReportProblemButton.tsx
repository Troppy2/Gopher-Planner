import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Check, Flag } from "lucide-react";
import { getMyReports } from "@/api/endpoints";
import { queryKeys } from "@/api/queryKeys";
import { Button, Modal } from "@/ui";
import { useSession } from "@/features/auth/session.store";
import { ReportProblemDialog } from "./ReportProblemDialog";
import type { ReportTarget } from "./reasons";

export function ReportProblemButton({ target }: { target: ReportTarget }) {
  const signedIn = useSession(s => s.signedIn);
  const [open, setOpen] = useState(false);
  const reports = useQuery({ queryKey: queryKeys.reports, queryFn: getMyReports, enabled: signedIn });
  if (!signedIn) return null;
  const existing = reports.data?.reports.find(r => r.status === "open" && r.targetType === target.type &&
    (target.type === "course" ? r.courseCode === target.courseCode : r.requirementId === target.requirementId));
  const Icon = existing ? Check : Flag;
  return <Modal open={open} onOpenChange={setOpen} size="md" title="Report a problem"
    subtitle={target.type === "course" ? [target.courseCode, target.title].filter(Boolean).join(": ") : target.label}
    trigger={<Button variant="quiet" size="sm" onClick={e => e.stopPropagation()}><Icon className="ic sm" aria-hidden />{existing ? "Reported" : "Report a problem"}</Button>}>
    {open && <ReportProblemDialog target={target} existing={existing} onClose={() => setOpen(false)} />}
  </Modal>;
}
