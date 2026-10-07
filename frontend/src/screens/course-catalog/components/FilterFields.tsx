import { Select } from "@/ui";

export type FilterKey = "subject" | "level" | "credits" | "term" | "requirement" | "availability";

export const FILTERS: Array<{ key: FilterKey; label: string; options: string[] }> = [
  { key: "subject", label: "Subject", options: ["CSCI", "MATH", "STAT", "SW", "PHYS", "WRIT"] },
  { key: "level", label: "Level", options: ["1xxx", "2xxx", "3xxx", "4xxx", "5xxx"] },
  { key: "credits", label: "Credits", options: ["1 to 2", "3", "4 or more"] },
  { key: "term", label: "Term offered", options: ["Fall", "Spring", "Summer"] },
  { key: "requirement", label: "Requirement type", options: ["Major core", "Math and stats", "Elective", "Liberal ed"] },
  { key: "availability", label: "Availability", options: ["Offered next term", "Not offered next term"] },
];

export function FilterFields({ values, onChange }: { values: Record<FilterKey, string>; onChange: (key: FilterKey, value: string) => void }) {
  return (
    <>
      {FILTERS.map((f) => (
        <Select
          key={f.key}
          className="ffield"
          label={f.label}
          value={values[f.key]}
          onChange={(v) => onChange(f.key, v)}
          options={[{ value: "", label: "Any" }, ...f.options]}
        />
      ))}
    </>
  );
}
