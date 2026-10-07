import { useId, useState } from "react";
import type { ReactNode } from "react";
import { Check } from "lucide-react";

interface ComboboxProps {
  label: ReactNode;
  value: string;
  onChange: (value: string) => void;
  options: string[];
  placeholder?: string;
  className?: string;
}

/** Free-text input with a filtered suggestion list. Typed text is kept even without a match. */
export function Combobox({ label, value, onChange, options, placeholder, className }: ComboboxProps) {
  const id = useId();
  const [open, setOpen] = useState(false);
  const [active, setActive] = useState(-1);
  const q = value.trim().toLowerCase();
  const matches = options.filter((o) => !q || o.toLowerCase().includes(q) || o === value);

  const pick = (v: string) => {
    onChange(v);
    setOpen(false);
    setActive(-1);
  };

  return (
    <div className={className ? `field ${className}` : "field"}>
      <label className="label" htmlFor={id}>
        {label}
      </label>
      <div className="combo">
        <input
          id={id}
          className="input"
          role="combobox"
          aria-expanded={open}
          aria-controls={`${id}-list`}
          aria-autocomplete="list"
          aria-activedescendant={active >= 0 ? `${id}-o${active}` : undefined}
          autoComplete="off"
          placeholder={placeholder}
          value={value}
          onFocus={() => setOpen(true)}
          onBlur={() => setTimeout(() => setOpen(false), 120)}
          onChange={(e) => {
            onChange(e.target.value);
            setOpen(true);
            setActive(-1);
          }}
          onKeyDown={(e) => {
            if (e.key === "ArrowDown") {
              e.preventDefault();
              setOpen(true);
              setActive((a) => Math.min(a + 1, matches.length - 1));
            } else if (e.key === "ArrowUp") {
              e.preventDefault();
              setActive((a) => Math.max(a - 1, 0));
            } else if (e.key === "Enter" && open && active >= 0 && matches[active]) {
              e.preventDefault();
              pick(matches[active]);
            } else if (e.key === "Escape") {
              setOpen(false);
            }
          }}
        />
        {open && (
          <ul className="combo-list" role="listbox" id={`${id}-list`}>
            {matches.length ? (
              matches.map((o, i) => (
                <li
                  key={o}
                  id={`${id}-o${i}`}
                  role="option"
                  aria-selected={i === active}
                  onMouseDown={(e) => {
                    e.preventDefault();
                    pick(o);
                  }}
                >
                  <span>{o}</span>
                  {o === value && <Check className="ic sm" aria-hidden />}
                </li>
              ))
            ) : (
              <li className="none">No matches. Your entry is kept.</li>
            )}
          </ul>
        )}
      </div>
    </div>
  );
}
