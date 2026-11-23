import { useEffect, useState } from "react";

export function CreditsField({ code, credits, onChange }: { code: string; credits: number; onChange: (code: string, credits: number) => void }) {
  const [value, setValue] = useState(String(credits));
  useEffect(() => setValue(String(credits)), [credits]);
  return <label className="term-picker credit-field"><span>Credits</span><input type="number" aria-label={`${code} credits`}
    min={0.5} max={12} step={0.5} value={value} onChange={event => {
      setValue(event.target.value);
      if (event.target.value && event.target.validity.valid) onChange(code, Number(event.target.value));
    }} onBlur={() => setValue(String(credits))} /></label>;
}
