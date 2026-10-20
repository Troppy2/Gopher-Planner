import type { PrerequisiteExpression } from "@/api/types";

interface Props {
  expression: PrerequisiteExpression;
}

function getText(value: unknown): string | null {
  if (!value || typeof value !== "object") {
    return null;
  }

  const text = (value as Record<string, unknown>).text;
  return typeof text === "string" && text.trim() ? text : null;
}

export function PrerequisiteTree({ expression }: Props) {
  if (expression.type === "course") {
    const courseCode =
      typeof expression.course_code === "string"
        ? expression.course_code
        : "Unknown course";

    return (
      <div className="prerequisite-course">
        <span className="prerequisite-bullet" aria-hidden="true" />
        <strong>{courseCode}</strong>
      </div>
    );
  }

  if (expression.type === "condition") {
    return (
      <div className="prerequisite-course prerequisite-condition">
        <span className="prerequisite-bullet" aria-hidden="true" />
        <span>{getText(expression) ?? "Additional condition"}</span>
      </div>
    );
  }

  if (expression.type === "any_of" || expression.type === "all_of") {
    const isAnyOf = expression.type === "any_of";
    const requirements = Array.isArray(expression.requirements)
      ? expression.requirements
      : [];

    return (
      <section
        className={`prerequisite-group ${
          isAnyOf ? "prerequisite-any" : "prerequisite-all"
        }`}
      >
        <div className="prerequisite-group-heading">
          <span className="prerequisite-group-type">
            {isAnyOf ? "ANY OF" : "ALL OF"}
          </span>
          <span>
            {isAnyOf ? "Complete at least one" : "Complete every requirement"}
          </span>
        </div>

        {requirements.length > 0 ? (
          <div className="prerequisite-children">
            {requirements.map((child, index) => (
              <PrerequisiteTree key={index} expression={child} />
            ))}
          </div>
        ) : (
          <p className="muted">Requirement details are unavailable.</p>
        )}
      </section>
    );
  }

  // Safely handle expression types this frontend doesn't recognize yet.
  return (
    <div className="prerequisite-course prerequisite-condition">
      <span className="prerequisite-bullet" aria-hidden="true" />
      <span>
        {getText(expression) ?? "Additional prerequisite requirement"}
      </span>
    </div>
  );
}
