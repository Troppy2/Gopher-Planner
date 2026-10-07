import { useId } from "react";
import type { InputHTMLAttributes, ReactNode, TextareaHTMLAttributes } from "react";
import { AlertTriangle } from "lucide-react";

interface FieldShellProps {
  label: ReactNode;
  hint?: ReactNode;
  error?: string;
  className?: string;
}

function Shell({ id, label, hint, error, className, children }: FieldShellProps & { id: string; children: ReactNode }) {
  return (
    <div className={className ? `field ${className}` : "field"}>
      <label className="label" htmlFor={id}>
        {label}
      </label>
      {children}
      {error ? (
        <span className="err" id={`${id}-err`}>
          <AlertTriangle className="ic sm" aria-hidden />
          {error}
        </span>
      ) : hint ? (
        <span className="hint" id={`${id}-hint`}>
          {hint}
        </span>
      ) : null}
    </div>
  );
}

const describedBy = (id: string, error?: string, hint?: ReactNode) => (error ? `${id}-err` : hint ? `${id}-hint` : undefined);

export function TextField({ label, hint, error, className, ...rest }: FieldShellProps & InputHTMLAttributes<HTMLInputElement>) {
  const id = useId();
  return (
    <Shell id={id} label={label} hint={hint} error={error} className={className}>
      <input id={id} className="input" aria-invalid={!!error} aria-describedby={describedBy(id, error, hint)} {...rest} />
    </Shell>
  );
}

export function TextArea({ label, hint, error, className, ...rest }: FieldShellProps & TextareaHTMLAttributes<HTMLTextAreaElement>) {
  const id = useId();
  return (
    <Shell id={id} label={label} hint={hint} error={error} className={className}>
      <textarea id={id} className="input" aria-invalid={!!error} aria-describedby={describedBy(id, error, hint)} {...rest} />
    </Shell>
  );
}
