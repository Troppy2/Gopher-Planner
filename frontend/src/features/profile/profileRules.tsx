import type { Options } from "@/api/types";
import { Callout } from "@/ui";

export const MIN_CREDITS = 12;
export const MAX_CREDITS = 25;
/** Above this, the plan works but the load is unusually heavy. */
export const HEAVY_CREDITS = 18;

export const creditChoices = Array.from({ length: MAX_CREDITS - MIN_CREDITS + 1 }, (_, i) => String(MIN_CREDITS + i));

/** Careers for the chosen major, always with an undecided option. */
export function careerOptions(options: Options | undefined, major: string) {
  const list = options?.careers?.[major] ?? [];
  return [{ value: "", label: "Not decided yet" }, ...list];
}

/** Keep the career only if the new major still offers it. */
export const careerForMajor = (options: Options | undefined, major: string, career: string) =>
  options?.careers?.[major]?.includes(career) ? career : "";

export function HeavyLoadNote({ credits }: { credits: number }) {
  if (credits <= HEAVY_CREDITS) return null;
  return (
    <Callout tone="warn" title={`${credits} credits is a heavy workload.`}>
      Discuss this load with your academic advisor before you commit to it.
    </Callout>
  );
}

/** Machine-mapped majors are selectable but flagged so students confirm with APAS or an advisor. */
export function UnverifiedMajorNote({ options, major }: { options?: Pick<Options, "unverifiedMajors">; major: string }) {
  if (!major || !options?.unverifiedMajors?.includes(major)) return null;
  return (
    <Callout tone="warn" title="This major's requirements are not verified yet.">
      They were mapped automatically from the catalog. Check your plan against APAS or with your advisor.
    </Callout>
  );
}
