export function SlotTag({ slot }: { slot?: string | null }) {
  return slot ? <span className="muted slot-tag">Gen ed: {slot}</span> : null;
}

export function ElectiveNote({ credits }: { credits?: number }) {
  return credits && credits > 0 ? <p className="muted elective-note">{credits} free elective credits still needed</p> : null;
}
