import { useEffect, useState } from "react";

export function CreditsField({ code, credits, onChange }: { code: string; credits: number; onChange: (code: string, credits: number) => void }) {
  const [value, setValue] = useState(String(credits));
  useEffect(() => setValue(String(credits)), [credits]);
  return <label className="credit-field"><span className="sr-only">Credits for {code}</span><input className="input num" inputMode="decimal"
    value={value} onChange={event => {
      const next = event.target.value;
      setValue(next);
      const n = Number(next);
      if (next && Number.isFinite(n) && n >= 0.5 && n <= 12 && n * 2 === Math.round(n * 2)) onChange(code, n);
    }} onBlur={() => setValue(String(credits))} /><span className="credit-unit" aria-hidden>cr</span></label>;
}
