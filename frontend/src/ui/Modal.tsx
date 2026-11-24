import type { ReactNode } from "react";
import * as Dialog from "@radix-ui/react-dialog";
import { X } from "lucide-react";
import { IconButton } from "./Button";
import "./modal.css";
interface Props {
  open: boolean; onOpenChange: (open: boolean) => void; title: ReactNode;
  subtitle?: ReactNode; children: ReactNode; footer?: ReactNode; size: "md" | "lg";
}
export function Modal({ open, onOpenChange, title, subtitle, children, footer, size }: Props) {
  return <Dialog.Root open={open} onOpenChange={onOpenChange}><Dialog.Portal>
    <Dialog.Overlay className="scrim" />
    <Dialog.Content className={`modal modal-${size}`} aria-describedby={undefined}>
      <header className="modal-header"><div><Dialog.Title asChild><h2>{title}</h2></Dialog.Title>
        {subtitle && <Dialog.Description asChild><p>{subtitle}</p></Dialog.Description>}
      </div><Dialog.Close asChild><IconButton label="Close"><X className="ic" aria-hidden /></IconButton></Dialog.Close></header>
      <div className="modal-content">{children}</div>
      {footer && <footer className="modal-footer">{footer}</footer>}
    </Dialog.Content>
  </Dialog.Portal></Dialog.Root>;
}
