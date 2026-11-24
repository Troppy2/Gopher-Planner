import type { ReactNode } from "react";
import * as Dialog from "@radix-ui/react-dialog";
import { X } from "lucide-react";
import { IconButton } from "./Button";
import "./modal.css";

interface Props {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  title: ReactNode;
  subtitle?: ReactNode;
  children: ReactNode;
  footer?: ReactNode;
  size: "md" | "lg";
  trigger?: ReactNode;
  /** The content manages its own padding, such as a sticky toolbar. */
  flush?: boolean;
  /** "dialog" focuses the dialog itself on open (long, read-first content); default is the first control in the body. */
  initialFocus?: "first" | "dialog";
}

/** Centered dialog with fixed header/footer and a scrolling body; mobile is a full-screen sheet. */
export function Modal({ open, onOpenChange, title, subtitle, children, footer, size, trigger, flush, initialFocus = "first" }: Props) {
  return <Dialog.Root open={open} onOpenChange={onOpenChange}>
    {trigger && <Dialog.Trigger asChild>{trigger}</Dialog.Trigger>}
    <Dialog.Portal>
      <Dialog.Overlay className="scrim modal-scrim" />
      <Dialog.Content className={`modal modal-${size}`} aria-describedby={undefined}
        onOpenAutoFocus={(event) => {
          // Start in the content, not on the close button: the first control, or the dialog itself.
          event.preventDefault();
          const dialog = event.currentTarget as HTMLElement | null;
          const first = initialFocus === "first"
            ? dialog?.querySelector<HTMLElement>(".modal-body :is(input, select, textarea, button, [href], [tabindex]:not([tabindex='-1'])):not(:disabled)")
            : null;
          (first ?? dialog)?.focus();
        }}>
        <header className="modal-header">
          <div><Dialog.Title asChild><h2>{title}</h2></Dialog.Title>
            {subtitle && <Dialog.Description asChild><p className="muted">{subtitle}</p></Dialog.Description>}
          </div>
          <Dialog.Close asChild><IconButton label="Close dialog"><X className="ic" aria-hidden /></IconButton></Dialog.Close>
        </header>
        <div className={flush ? "modal-body flush" : "modal-body"}>{children}</div>
        {footer && <footer className="modal-footer">{footer}</footer>}
      </Dialog.Content>
    </Dialog.Portal>
  </Dialog.Root>;
}
