import { useRef, useState } from "react";
import type { ReactNode } from "react";
import { Check, Minus, Plus, Upload } from "lucide-react";
import { Button, IconButton } from "./Button";
import { cn } from "@/lib/cn";

export function Checkbox({ checked, onChange, children }: { checked: boolean; onChange: (checked: boolean) => void; children: ReactNode }) {
  return (
    <button type="button" role="checkbox" aria-checked={checked} className="chk" onClick={() => onChange(!checked)}>
      <span className="bx">
        <Check className="ic sm" aria-hidden />
      </span>
      {children}
    </button>
  );
}

interface StepperProps {
  labelId: string;
  value: number;
  min: number;
  max: number;
  onChange: (value: number) => void;
  format: (value: number) => string;
  decLabel: string;
  incLabel: string;
}

export function Stepper({ labelId, value, min, max, onChange, format, decLabel, incLabel }: StepperProps) {
  return (
    <div className="stepper" role="group" aria-labelledby={labelId}>
      <IconButton label={decLabel} disabled={value <= min} onClick={() => onChange(value - 1)}>
        <Minus className="ic" aria-hidden />
      </IconButton>
      <output className="num" aria-live="polite">
        {format(value)}
      </output>
      <IconButton label={incLabel} disabled={value >= max} onClick={() => onChange(value + 1)}>
        <Plus className="ic" aria-hidden />
      </IconButton>
    </div>
  );
}

interface DropzoneProps {
  title: string;
  hint: string;
  accept: string;
  onFile: (file: File) => void;
}

export function Dropzone({ title, hint, accept, onFile }: DropzoneProps) {
  const input = useRef<HTMLInputElement>(null);
  const [over, setOver] = useState(false);
  return (
    <div
      className={cn("drop", over && "over")}
      onDragOver={(e) => {
        e.preventDefault();
        setOver(true);
      }}
      onDragLeave={() => setOver(false)}
      onDrop={(e) => {
        e.preventDefault();
        setOver(false);
        const f = e.dataTransfer.files[0];
        if (f) onFile(f);
      }}
    >
      <Upload className="ic drop-ic" aria-hidden />
      <b>{title}</b>
      <span className="hint">{hint}</span>
      <Button onClick={() => input.current?.click()}>Choose file</Button>
      <input
        ref={input}
        type="file"
        accept={accept}
        hidden
        onChange={(e) => {
          const f = e.target.files?.[0];
          if (f) onFile(f);
          e.target.value = "";
        }}
      />
    </div>
  );
}
