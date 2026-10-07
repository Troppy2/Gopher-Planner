import { useRef, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { CheckCircle2, PenLine, RefreshCw, XCircle } from "lucide-react";
import { getOptions, getProfile, updateProfile } from "@/api/endpoints";
import { mockFlags, resetMockDb } from "@/api/mock/mockDb";
import { queryKeys } from "@/api/queryKeys";
import type { Options, Profile } from "@/api/types";
import { Button, Checkbox, DemoToggle, EmptyState, Select, Stepper, TextField } from "@/ui";
import { useSession } from "@/features/auth/session.store";
import { usePlanDraft } from "@/features/plan/plan.store";
import { careerForMajor, careerOptions, HeavyLoadNote, MAX_CREDITS, MIN_CREDITS } from "@/features/profile/profileRules";
import "./settings.css";

type Form = Pick<Profile, "name" | "major" | "standing" | "careerGoals" | "creditLoad" | "graduationTarget">;
const pick = (p: Profile): Form => ({
  name: p.name,
  major: p.major,
  standing: p.standing,
  careerGoals: p.careerGoals,
  creditLoad: p.creditLoad,
  graduationTarget: p.graduationTarget,
});
const same = (a: Form, b: Form) => (Object.keys(a) as Array<keyof Form>).every((k) => a[k] === b[k]);

export default function SettingsScreen() {
  const profileQ = useQuery({ queryKey: queryKeys.profile, queryFn: getProfile });
  const { data: options } = useQuery({ queryKey: queryKeys.options, queryFn: getOptions });

  if (profileQ.isError) {
    return (
      <div className="page narrow">
        <EmptyState
          title="We couldn't load your settings"
          action={
            <Button onClick={() => profileQ.refetch()}>
              <RefreshCw className="ic sm" aria-hidden />
              Try again
            </Button>
          }
        >
          Check your connection and try again.
        </EmptyState>
      </div>
    );
  }
  if (!profileQ.data) {
    return (
      <div className="page narrow">
        <h1 className="title">Settings</h1>
      </div>
    );
  }
  return <SettingsForm profile={profileQ.data} options={options} />;
}

function SettingsForm({ profile, options }: { profile: Profile; options?: Options }) {
  const qc = useQueryClient();
  const [saved, setSaved] = useState<Form>(pick(profile));
  const [form, setForm] = useState<Form>(pick(profile));
  const [nameError, setNameError] = useState("");
  const [failPreview, setFailPreview] = useState(false);
  const nameRef = useRef<HTMLDivElement>(null);
  const signOut = useSession((s) => s.signOut);

  // Optimistic: the form reads as saved the moment you press Save; a failure rolls it back.
  const save = useMutation({
    mutationFn: (f: Form) => updateProfile(f),
    onMutate: (f) => {
      const prevSaved = saved;
      const prevProfile = qc.getQueryData<Profile>(queryKeys.profile);
      setSaved(f);
      if (prevProfile) qc.setQueryData(queryKeys.profile, { ...prevProfile, ...f });
      return { prevSaved, prevProfile };
    },
    onError: (_e, _f, ctx) => {
      if (!ctx) return;
      setSaved(ctx.prevSaved);
      if (ctx.prevProfile) qc.setQueryData(queryKeys.profile, ctx.prevProfile);
    },
    onSuccess: (p) => {
      qc.setQueryData(queryKeys.profile, p);
      qc.invalidateQueries({ queryKey: queryKeys.summary });
      setFailPreview(false);
    },
  });

  const dirty = !same(form, saved);
  const state = save.isError && dirty ? "error" : dirty ? "unsaved" : "saved";
  const set = (patch: Partial<Form>) => {
    setForm({ ...form, ...patch });
    if (patch.name?.trim()) setNameError("");
    if (save.isError) save.reset();
  };

  const onSave = () => {
    if (!form.name.trim()) {
      setNameError("Enter your name so we can personalize your plan.");
      nameRef.current?.querySelector("input")?.focus();
      return;
    }
    mockFlags.failNextSettingsSave = failPreview;
    const next = { ...form, name: form.name.trim() };
    setForm(next);
    save.mutate(next);
  };
  const onDiscard = () => {
    setForm(saved);
    setNameError("");
    save.reset();
  };

  const STATE = {
    saved: { icon: <CheckCircle2 className="ic sm" aria-hidden />, text: "Saved" },
    unsaved: { icon: <PenLine className="ic sm" aria-hidden />, text: "Unsaved changes" },
    error: { icon: <XCircle className="ic sm" aria-hidden />, text: "Could not save" },
  }[state];

  return (
    <div className="page narrow">
      <div className="pg-head">
        <h1 className="title">Settings</h1>
        <span className={`sstate ${state}`} role="status">
          {STATE.icon}
          {STATE.text}
        </span>
      </div>

      <form
        noValidate
        onSubmit={(e) => {
          e.preventDefault();
          onSave();
        }}
      >
        <section className="sec surf" aria-labelledby="s-profile">
          <h2 id="s-profile">Profile</h2>
          <div className="sgrid" ref={nameRef}>
            <TextField label="Name" autoComplete="name" value={form.name} onChange={(e) => set({ name: e.target.value })} error={nameError} />
          </div>
        </section>

        <section className="sec surf" aria-labelledby="s-goals">
          <h2 id="s-goals">Academic goals</h2>
          <div className="sgrid">
            <Select
              label="Major or degree program"
              value={form.major}
              onChange={(major) => set({ major, careerGoals: careerForMajor(options, major, form.careerGoals) })}
              options={options?.majors ?? [form.major]}
            />
            <Select label="Grade standing" value={form.standing} onChange={(standing) => set({ standing })} options={options?.standings ?? [form.standing]} />
            <Select
              className="span2"
              label="Career goal"
              value={form.careerGoals}
              onChange={(careerGoals) => set({ careerGoals })}
              options={careerOptions(options, form.major)}
            />
          </div>
        </section>

        <section className="sec surf" aria-labelledby="s-plan">
          <h2 id="s-plan">Planning preferences</h2>
          <div className="sgrid">
            <div className="field">
              <span className="label" id="load-l">
                Preferred credits per term
              </span>
              <Stepper
                labelId="load-l"
                value={form.creditLoad}
                min={MIN_CREDITS}
                max={MAX_CREDITS}
                onChange={(creditLoad) => set({ creditLoad })}
                format={(v) => `${v} credits`}
                decLabel="Fewer credits"
                incLabel="More credits"
              />
              <span className="hint">
                {MIN_CREDITS} to {MAX_CREDITS} credits.
              </span>
            </div>
            <Select
              label="Desired graduation"
              value={form.graduationTarget}
              onChange={(graduationTarget) => set({ graduationTarget })}
              options={options?.graduationTargets ?? [form.graduationTarget]}
            />
            <div className="span2">
              <HeavyLoadNote credits={form.creditLoad} />
            </div>
          </div>
        </section>

        <div className="sfoot">
          <Button type="submit" disabled={!dirty}>
            Save changes
          </Button>
        </div>
      </form>

      <DemoToggle>
        <Checkbox checked={failPreview} onChange={setFailPreview}>
          Preview only: make the next save fail
        </Checkbox>
        <Button
          variant="ghost"
          size="sm"
          onClick={() => {
            resetMockDb();
            usePlanDraft.getState().clear();
            qc.clear();
            signOut();
            location.assign("/login");
          }}
        >
          Reset demo data
        </Button>
      </DemoToggle>

      {state !== "saved" && (
        <div className="savebar" role="status">
          <span className="msg">
            <b>{state === "error" ? "Could not save. Check your connection and try again." : "Unsaved changes"}</b>
          </span>
          <Button variant="ghost" size="sm" onClick={onDiscard}>
            Discard
          </Button>
          <Button size="sm" onClick={onSave}>
            {state === "error" ? "Try again" : "Save changes"}
          </Button>
        </div>
      )}
    </div>
  );
}
