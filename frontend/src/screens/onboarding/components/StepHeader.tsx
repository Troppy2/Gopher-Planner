export function StepHeader({ step, total }: { step: number; total: number }) {
  return (
    <div className="steps">
      <span className="num">
        {step} of {total}
      </span>
      <div className="tr" aria-hidden>
        {Array.from({ length: total }, (_, i) => (
          <i key={i} className={i < step ? "on" : undefined} />
        ))}
      </div>
    </div>
  );
}
