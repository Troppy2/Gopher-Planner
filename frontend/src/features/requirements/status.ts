import type { RequirementStatus } from "@/api/types";
import { CheckCircle2, CircleDashed, AlertCircle, HelpCircle } from "lucide-react";
/** One scannable status per requirement: done, covered by the plan, or short. */
export function chip(completed: RequirementStatus, projected: RequirementStatus) {
  if (completed === "satisfied") return { cls: "met", text: "Met", Icon: CheckCircle2 };
  if (projected === "satisfied") return { cls: "track", text: "On track", Icon: CircleDashed };
  if (projected === "needs_review") return { cls: "review", text: "Needs review", Icon: HelpCircle };
  return { cls: "short", text: "Short", Icon: AlertCircle };
}


