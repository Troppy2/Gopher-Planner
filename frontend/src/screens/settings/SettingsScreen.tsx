import { Link } from "react-router";
import { useRef, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { RefreshCw } from "lucide-react";
import { getOptions, getProfile, updateProfile } from "@/api/endpoints";
import { queryKeys } from "@/api/queryKeys";
import type { Options, Profile } from "@/api/types";
import { Button, Callout, Combobox, EmptyState, SaveToast, Select, Stepper, TextField } from "@/ui";
import { useLeaveWarning } from "@/hooks/useLeaveWarning";
import { useAutosave } from "@/hooks/useAutosave";
import { HeavyLoadNote, UnverifiedMajorNote, MAX_CREDITS, MIN_CREDITS } from "@/features/profile/profileRules";
import { CourseworkEditor } from "@/features/coursework/CourseworkEditor";
import { DeleteAccount } from "@/features/account/DeleteAccount";
import { usePlanDraft } from "@/features/plan/plan.store";
import { SettingsSkeleton } from "@/features/loading/ScreenSkeletons";
import "./settings.css";

type Form = Pick<Profile, "name" | "major" | "standing" | "creditLoad" | "graduationTarget">;
const pick = (p: Profile): Form => ({
  name: p.name,
  major: p.major,
  standing: p.standing,
  creditLoad: p.creditLoad,
  graduationTarget: p.graduationTarget,
});
const same = (a: Form, b: Form) => (Object.keys(a) as Array<keyof Form>).every((k) => a[k] === b[k]);

export default function SettingsScreen() {
  const profileQ = useQuery({ queryKey: queryKeys.profile, queryFn: getProfile });
  const optionsQ = useQuery({ queryKey: queryKeys.options, queryFn: getOptions });

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
    return <SettingsSkeleton />;
  }
  return <>
    {optionsQ.isError && <Callout tone="warn" title="Could not load the major list."><Button variant="ghost" onClick={() => optionsQ.refetch()}>Retry major list</Button></Callout>}
    <SettingsForm profile={profileQ.data} options={optionsQ.data} />
  </>;
}

function SettingsForm({ profile, options }: { profile: Profile; options?: Options }) {
  const qc = useQueryClient();
  const [saved, setSaved] = useState<Form>(pick(profile));
  const [form, setForm] = useState<Form>(pick(profile));
  const [nameError, setNameError] = useState("");
  const nameRef = useRef<HTMLDivElement>(null);

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
    onSuccess: (p, _f, ctx) => {
      if (p.major !== ctx?.prevProfile?.major) usePlanDraft.getState().clear();
      qc.setQueryData(queryKeys.profile, p);
      qc.invalidateQueries({ queryKey: queryKeys.plan });
      qc.invalidateQueries({ queryKey: queryKeys.summary });
    },
  });

  const dirty = !same(form, saved);
  const state = save.isError && dirty ? "error" : dirty ? "unsaved" : "saved";
  useLeaveWarning(dirty);
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
    const next = { ...form, name: form.name.trim() };
    setForm(next);
    save.mutate(next);
  };
  // Profile changes save on their own once the name is filled in; the bar only reports problems.
  useAutosave({
    enabled: dirty && !!form.name.trim() && !save.isPending,
    key: JSON.stringify(form),
    save: () => save.mutate({ ...form, name: form.name.trim() }),
    failed: save.isError,
  });
  const onDiscard = () => {
    setForm(saved);
    setNameError("");
    save.reset();
  };

  // Waiting out the autosave delay counts as saving, so the toast appears as soon as you edit.
  const saving = (state === "unsaved" && !!form.name.trim()) || save.isPending;
  const nameHint = state === "unsaved" && !form.name.trim() ? "Add your name to save your changes." : "";

  return (
    <div className="page narrow">
      <div className="pg-head">
        <h1 className="title">Settings</h1>
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
            <TextField label="Name" autoComplete="name" value={form.name} onChange={(e) => set({ name: e.target.value })} error={nameError || nameHint} />
          </div>
        </section>

        <section className="sec surf" aria-labelledby="s-goals">
          <h2 id="s-goals">Academic goals</h2>
          <div className="sgrid">
            <Combobox
              label="Major or degree program"
              value={form.major}
              onChange={(major) => set({ major })}
              options={options?.majors ?? [form.major]}
              placeholder="Start typing, for example Computer Science"
            />
            <div className="span2">
              <UnverifiedMajorNote options={options} major={form.major} />
            </div>
            <Select label="Grade standing" value={form.standing} onChange={(standing) => set({ standing })} options={options?.standings ?? [form.standing]} />
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

      </form>

      <CourseworkEditor />

      <DeleteAccount />

      <nav className="settings-legal muted" aria-label="Legal and contact">
        <Link to="/privacy">Privacy</Link>
        <Link to="/terms">Terms</Link>
        <Link to="/contact">Contact</Link>
      </nav>

      <SaveToast saving={saving} failed={state === "error"} />
      {state === "error" && (
        <div className="savebar" role="alert">
          <span className="msg">
            <b>Couldn't save your profile. Check your connection and try again.</b>
          </span>
          <Button variant="ghost" size="sm" onClick={onDiscard}>
            Undo changes
          </Button>
          <Button size="sm" onClick={onSave}>
            Try again
          </Button>
        </div>
      )}
    </div>
  );
}
