import { useState } from "react";
import { useNavigate } from "react-router";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ArrowLeft } from "lucide-react";
import { getOptions, getProfile, updateProfile } from "@/api/endpoints";
import { queryKeys } from "@/api/queryKeys";
import { Button, Callout, Combobox, Select, Spinner, TextField } from "@/ui";
import { careerForMajor, careerOptions, creditChoices, HeavyLoadNote } from "@/features/profile/profileRules";
import { StepHeader } from "./components/StepHeader";
import { useOnboarding } from "./onboarding.store";
import type { ProfileDraft } from "./onboarding.store";
import "./onboarding.css";

export default function ProfileScreen() {
  const navigate = useNavigate();
  const qc = useQueryClient();
  const { data: profile } = useQuery({ queryKey: queryKeys.profile, queryFn: getProfile });
  const { data: options } = useQuery({ queryKey: queryKeys.options, queryFn: getOptions });
  const { profile: saved, setProfile } = useOnboarding();
  const [touched, setTouched] = useState(false);

  const draft: ProfileDraft = saved ?? {
    name: profile?.name ?? "",
    standing: profile?.standing ?? "Freshman",
    major: profile?.major ?? "",
    careerGoals: profile?.careerGoals ?? "",
    creditLoad: "",
    graduationTarget: "",
  };
  const set = (patch: Partial<ProfileDraft>) => setProfile({ ...draft, ...patch });

  const errors = {
    name: !draft.name.trim() ? "Enter your name so we can personalize your plan." : "",
    major: !draft.major.trim() ? "Choose your major or degree program." : "",
  };
  const valid = !errors.name && !errors.major;

  const save = useMutation({
    mutationFn: () =>
      updateProfile({
        name: draft.name.trim(),
        standing: draft.standing,
        major: draft.major.trim(),
        careerGoals: draft.careerGoals.trim(),
        creditLoad: draft.creditLoad ? Number(draft.creditLoad) : 15,
        graduationTarget: draft.graduationTarget || profile?.graduationTarget || "Spring 2028",
      }),
    onSuccess: (p) => {
      qc.setQueryData(queryKeys.profile, p);
      navigate("/onboarding/building");
    },
  });

  return (
    <>
      <StepHeader step={2} total={2} />
      <h1 className="title">Build your profile</h1>
      <form
        className="form2 surf"
        noValidate
        onSubmit={(e) => {
          e.preventDefault();
          setTouched(true);
          if (valid) save.mutate();
        }}
      >
        <TextField label="Name" autoComplete="name" value={draft.name} onChange={(e) => set({ name: e.target.value })} error={touched ? errors.name : ""} />
        <Select label="Grade standing" value={draft.standing} onChange={(standing) => set({ standing })} options={options?.standings ?? [draft.standing]} />
        <div className="span2">
          <Combobox
            label="Major or degree program"
            value={draft.major}
            onChange={(major) => set({ major, careerGoals: careerForMajor(options, major, draft.careerGoals) })}
            options={options?.majors ?? []}
            placeholder="Start typing, for example Computer Science"
          />
          {touched && errors.major && <span className="err">{errors.major}</span>}
        </div>
        <Select
          className="span2"
          label="Career goal"
          value={draft.careerGoals}
          onChange={(careerGoals) => set({ careerGoals })}
          options={careerOptions(options, draft.major)}
        />
        <Select
          label={
            <>
              Credits per term <span className="opt">(optional)</span>
            </>
          }
          value={draft.creditLoad}
          onChange={(creditLoad) => set({ creditLoad })}
          options={[{ value: "", label: "Not set" }, ...creditChoices]}
        />
        <Select
          label={
            <>
              Graduation target <span className="opt">(optional)</span>
            </>
          }
          value={draft.graduationTarget}
          onChange={(graduationTarget) => set({ graduationTarget })}
          options={[{ value: "", label: "Not set" }, ...(options?.graduationTargets ?? [])]}
        />
        {draft.creditLoad && (
          <div className="span2">
            <HeavyLoadNote credits={Number(draft.creditLoad)} />
          </div>
        )}
        <p className="hint span2">If you leave these blank, we plan 15 credits per term and ask you to confirm a graduation target before the plan is final.</p>
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
    </>
  );
}
