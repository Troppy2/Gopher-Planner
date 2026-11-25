import { useRef, useState } from "react";
import { useNavigate } from "react-router";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ArrowLeft } from "lucide-react";
import { getOptions, getProfile, updateProfile } from "@/api/endpoints";
import { queryKeys } from "@/api/queryKeys";
import { Button, Callout, Combobox, Select, Spinner, TextField } from "@/ui";
import { creditChoices, HeavyLoadNote, UnverifiedMajorNote } from "@/features/profile/profileRules";
import { StepHeader } from "./components/StepHeader";
import { useOnboarding } from "./onboarding.store";
import type { ProfileDraft } from "./onboarding.store";
import { usePlanDraft } from "@/features/plan/plan.store";
import { useSession } from "@/features/auth/session.store";
import { upcomingTerms } from "@/lib/terms";
import { FieldsSkeleton } from "@/features/loading/ScreenSkeletons";
import { SkeletonRegion } from "@/ui/Skeleton";
import "./onboarding.css";

export default function ProfileScreen() {
  const navigate = useNavigate();
  const qc = useQueryClient();
  const profileQ = useQuery({ queryKey: queryKeys.profile, queryFn: getProfile });
  const profile = profileQ.data;
  const optionsQ = useQuery({ queryKey: queryKeys.options, queryFn: getOptions });
  const options = optionsQ.data;
  const { profile: saved, setProfile } = useOnboarding();
  const signedInName = useSession((s) => s.user?.name ?? "");
  const [touched, setTouched] = useState(false);
  const [majorFocused, setMajorFocused] = useState(false);
  const form = useRef<HTMLFormElement>(null);

  const draft: ProfileDraft = saved ?? {
    // Google already gave us a name; prefill it instead of asking again.
    name: profile?.name || signedInName,
    standing: profile?.standing || "Freshman",
    major: profile?.major ?? "",
    creditLoad: "",
    graduationTarget: profile?.graduationTarget ?? "",
  };
  const set = (patch: Partial<ProfileDraft>) => setProfile({ ...draft, ...patch });

  const errors = {
    name: !draft.name.trim() ? "Enter your name so we can personalize your plan." : "",
    major: !draft.major.trim() ? "Choose your major or degree program." : "",
  };
  const valid = !errors.name && !errors.major;
  // Free text is allowed, but a major we have no requirements for should not pass silently.
  const unknownMajor = !!options?.majors.length && !!draft.major.trim() && !options.majors.includes(draft.major.trim());
  const targets = upcomingTerms();
  if (draft.graduationTarget && !targets.includes(draft.graduationTarget)) targets.unshift(draft.graduationTarget);

  const save = useMutation({
    mutationFn: () =>
      updateProfile({
        name: draft.name.trim(),
        standing: draft.standing,
        major: draft.major.trim(),
        creditLoad: draft.creditLoad ? Number(draft.creditLoad) : 15,
        // Blank means a standard four-year window; the planner handles an empty target.
        graduationTarget: draft.graduationTarget,
      }),
    onSuccess: (p) => {
      if (p.major !== profile?.major) usePlanDraft.getState().clear();
      qc.setQueryData(queryKeys.profile, p);
      void qc.invalidateQueries({ queryKey: queryKeys.plan });
      void qc.invalidateQueries({ queryKey: queryKeys.summary });
      navigate("/onboarding/building");
    },
  });

  return (
    <>
      <StepHeader step={2} total={3} />
      <h1 className="title">Build your profile</h1>
      {!profile && !saved && profileQ.isPending ? (
        <SkeletonRegion label="profile"><div className="surf skeleton-section"><FieldsSkeleton count={6} /></div></SkeletonRegion>
      ) : profileQ.isError && !saved ? (
        <Callout tone="error" title="Could not load your profile."><Button onClick={() => profileQ.refetch()}>Try again</Button></Callout>
      ) : <>
      {optionsQ.isError && <Callout tone="warn" title="Could not load the major list."><Button variant="ghost" onClick={() => optionsQ.refetch()}>Retry major list</Button></Callout>}
      <form
        ref={form}
        className="form2 surf"
        noValidate
        onSubmit={(e) => {
          e.preventDefault();
          setTouched(true);
          if (valid) save.mutate();
          // Move focus to the first field that needs fixing once its error renders.
          else requestAnimationFrame(() => form.current?.querySelector<HTMLElement>('[aria-invalid="true"]')?.focus());
        }}
      >
        <TextField label="Name" autoComplete="name" value={draft.name} onChange={(e) => set({ name: e.target.value })} error={touched ? errors.name : ""} />
        <Select label="Grade standing" value={draft.standing} onChange={(standing) => set({ standing })} options={options?.standings ?? [draft.standing]} />
        <div
          className="span2"
          onFocus={() => setMajorFocused(true)}
          onBlur={(e) => {
            if (!e.currentTarget.contains(e.relatedTarget)) setMajorFocused(false);
          }}
        >
          <Combobox
            label="Major or degree program"
            value={draft.major}
            onChange={(major) => set({ major })}
            options={options?.majors ?? []}
            placeholder="Start typing, for example Computer Science"
            error={touched ? errors.major : undefined}
          />
          <UnverifiedMajorNote options={options} major={draft.major} />
          {unknownMajor && !majorFocused && (
            <Callout tone="warn" title="We don't have requirements for this major.">
              Pick a program from the list. If yours isn't there, you can continue, but your plan will only include courses you add yourself.
            </Callout>
          )}
        </div>
        <Select
          label={
            <>
              Credits per term <span className="muted">(optional)</span>
            </>
          }
          value={draft.creditLoad}
          onChange={(creditLoad) => set({ creditLoad })}
          options={[{ value: "", label: "Not set" }, ...creditChoices]}
        />
        <Select
          label={
            <>
              Graduation target <span className="muted">(optional)</span>
            </>
          }
          value={draft.graduationTarget}
          onChange={(graduationTarget) => set({ graduationTarget })}
          options={[{ value: "", label: "Not set" }, ...targets]}
        />
        {draft.creditLoad && (
          <div className="span2">
            <HeavyLoadNote credits={Number(draft.creditLoad)} />
          </div>
        )}
        <p className="hint span2">If you leave these blank, we plan 15 credits per term over a standard four years. You can change both later in Settings.</p>
        {save.isError && (
          <div className="span2">
            <Callout tone="error" title="Could not save your profile.">
              Check your connection and try again.
            </Callout>
          </div>
        )}
        <div className="actions span2">
          <Button variant="ghost" onClick={() => navigate("/onboarding/coursework")}>
            <ArrowLeft className="ic sm" aria-hidden />
            Back
          </Button>
          <Button type="submit" disabled={save.isPending}>
            {save.isPending && <Spinner />}
            Finish and build plan
          </Button>
        </div>
      </form>
      </>}
    </>
  );
}
