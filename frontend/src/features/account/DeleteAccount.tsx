import { useState } from "react";
import { useNavigate } from "react-router";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import * as Dialog from "@radix-ui/react-dialog";
import { Trash2 } from "lucide-react";
import { deleteAccount } from "@/api/endpoints";
import { useSession } from "@/features/auth/session.store";
import { usePlanDraft } from "@/features/plan/plan.store";
import { useOnboarding } from "@/screens/onboarding/onboarding.store";
import { Button, Callout, Spinner, TextField } from "@/ui";

const PHRASE = "delete";

/** Settings section that permanently deletes the account after a typed confirmation. */
export function DeleteAccount() {
  const [open, setOpen] = useState(false);
  const [typed, setTyped] = useState("");
  const navigate = useNavigate();
  const qc = useQueryClient();

  const remove = useMutation({
    mutationFn: deleteAccount,
    onSuccess: () => {
      qc.clear();
      usePlanDraft.getState().clear();
      useOnboarding.getState().reset();
      useSession.getState().clear();
      navigate("/login", { replace: true });
    },
  });

  const confirmed = typed.trim().toLowerCase() === PHRASE;
  const onOpenChange = (next: boolean) => {
    if (remove.isPending) return;
    setOpen(next);
    if (!next) {
      setTyped("");
      remove.reset();
    }
  };

  return (
    <section className="sec surf" aria-labelledby="s-delete">
      <h2 id="s-delete">Delete account</h2>
      <p className="muted del-copy">
        Permanently delete your account, profile, coursework, uploaded audit results, and plan. This can't be undone.
      </p>
      <Dialog.Root open={open} onOpenChange={onOpenChange}>
        <Dialog.Trigger asChild>
          <Button variant="ghost" className="danger">
            <Trash2 className="ic sm" aria-hidden />
            Delete account
          </Button>
        </Dialog.Trigger>
        <Dialog.Portal>
          <Dialog.Overlay className="scrim" />
          <Dialog.Content className="confirm-dialog surf">
            <Dialog.Title asChild>
              <h2>Delete your account?</h2>
            </Dialog.Title>
            <Dialog.Description>
              This permanently removes your profile, coursework, audit results, and four-year plan, and signs you out.
              You can sign in again later, but you'll start from scratch.
            </Dialog.Description>
            <form
              noValidate
              onSubmit={(e) => {
                e.preventDefault();
                if (confirmed && !remove.isPending) remove.mutate();
              }}
            >
              <TextField
                label={<>Type <b>{PHRASE}</b> to confirm</>}
                autoComplete="off"
                value={typed}
                onChange={(e) => setTyped(e.target.value)}
              />
              {remove.isError && (
                <Callout tone="error" title="Couldn't delete your account.">
                  Nothing was removed. Check your connection and try again.
                </Callout>
              )}
              <div className="confirm-actions">
                <Dialog.Close asChild>
                  <Button variant="ghost" disabled={remove.isPending}>Cancel</Button>
                </Dialog.Close>
                <Button type="submit" className="danger" disabled={!confirmed || remove.isPending}>
                  {remove.isPending && <Spinner />}
                  Delete account
                </Button>
              </div>
            </form>
          </Dialog.Content>
        </Dialog.Portal>
      </Dialog.Root>
    </section>
  );
}
