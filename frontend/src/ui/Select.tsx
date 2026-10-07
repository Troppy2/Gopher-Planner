import { useId } from "react";
import type { ReactNode } from "react";
import * as RS from "@radix-ui/react-select";
import { Check, ChevronDown } from "lucide-react";

export interface Option {
  value: string;
  label: string;
}

// Radix forbids "" as an item value, so empty maps to a sentinel.
const NONE = "__none__";

interface SelectProps {
  label?: ReactNode;
  /** Accessible name when there is no visible label. */
  ariaLabel?: string;
  value: string;
  onChange: (value: string) => void;
  options: Array<Option | string>;
  className?: string;
}

export function Select({ label, ariaLabel, value, onChange, options, className }: SelectProps) {
  const id = useId();
  const opts = options.map((o) => (typeof o === "string" ? { value: o, label: o } : o));
  const control = (
    <RS.Root value={value === "" ? NONE : value} onValueChange={(v) => onChange(v === NONE ? "" : v)}>
      <RS.Trigger className="sel-btn" id={id} aria-label={label ? undefined : ariaLabel}>
        <RS.Value />
        <RS.Icon asChild>
          <ChevronDown className="ic" aria-hidden />
        </RS.Icon>
      </RS.Trigger>
      <RS.Portal>
        <RS.Content className="sel-list" position="popper" sideOffset={6}>
          <RS.Viewport>
            {opts.map((o) => (
              <RS.Item key={o.value || NONE} value={o.value === "" ? NONE : o.value} className="sel-item">
                <RS.ItemText>{o.label}</RS.ItemText>
                <RS.ItemIndicator>
                  <Check className="ic sm" aria-hidden />
                </RS.ItemIndicator>
              </RS.Item>
            ))}
          </RS.Viewport>
        </RS.Content>
      </RS.Portal>
    </RS.Root>
  );
  if (!label) return <div className={className}>{control}</div>;
  return (
    <div className={className ? `field ${className}` : "field"}>
      <label className="label" htmlFor={id}>
        {label}
      </label>
      {control}
    </div>
  );
}
