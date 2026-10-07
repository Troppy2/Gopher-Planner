import type { ReactNode } from "react";
import * as Dialog from "@radix-ui/react-dialog";
import { X } from "lucide-react";
import { IconButton } from "./Button";

interface Props {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  title: ReactNode;
  subtitle?: ReactNode;
  children: ReactNode;
  footer?: ReactNode;
  closeLabel?: string;
}

/** Side drawer on desktop, bottom sheet under 768px (see index.css). Radix traps and restores focus. */
export function Drawer({ open, onOpenChange, title, subtitle, children, footer, closeLabel = "Close" }: Props) {
  return (
    <Dialog.Root open={open} onOpenChange={onOpenChange}>
      <Dialog.Portal>
        <Dialog.Overlay className="scrim" />
        <Dialog.Content className="drawer" aria-describedby={undefined}>
          <div className="grab" aria-hidden />
          <div className="dh">
            <div>
              <Dialog.Title asChild>
                <h2>{title}</h2>
              </Dialog.Title>
              {subtitle && <p>{subtitle}</p>}
            </div>
            <Dialog.Close asChild>
              <IconButton label={closeLabel}>
                <X className="ic" aria-hidden />
              </IconButton>
            </Dialog.Close>
          </div>
          <div className="db">{children}</div>
          {footer && <div className="df">{footer}</div>}
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}
