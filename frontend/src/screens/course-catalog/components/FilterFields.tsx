import { Select } from "@/ui";

export type FilterKey =
  | "subject"
  | "level"
  | "credits"
  | "term"
  | "availability";

export const FILTERS: Array<{
  key: FilterKey;
  label: string;
  options: string[];
}> = [
  {
    key: "level",
    label: "Level",
    options: ["1xxx", "2xxx", "3xxx", "4xxx", "5xxx"],
  },
  {
    key: "credits",
    label: "Credits",
    options: ["1 to 2", "3", "4 or more"],
  },
  {
    key: "term",
    label: "Term offered",
    options: ["Fall", "Spring", "Summer"],
  },
  {
    key: "availability",
    label: "Availability",
    options: ["Offered next term", "Not offered next term"],
  },
];

export function FilterFields({
  values,
  onChange,
}: {
  values: Record<FilterKey, string>;
  onChange: (key: FilterKey, value: string) => void;
}) {
  return (
    <>
      <div className="field ffield">
        <label className="label" htmlFor="filter-subject">Subject</label>
        <input id="filter-subject" className="input" placeholder="Any, e.g. STAT" autoCapitalize="characters" spellCheck={false}
          maxLength={6} value={values.subject} onChange={(e) => onChange("subject", e.target.value.toUpperCase().replace(/[^A-Z&]/g, ""))} />
      </div>
      {FILTERS.map((filter) => (
        <Select
          key={filter.key}
          className="ffield"
          label={filter.label}
          value={values[filter.key]}
          onChange={(value) => onChange(filter.key, value)}
          options={[
            { value: "", label: "Any" },
            ...filter.options.map((option) => ({
              value: option,
              label: option,
            })),
          ]}
        />
      ))}
    </>
  );
}
