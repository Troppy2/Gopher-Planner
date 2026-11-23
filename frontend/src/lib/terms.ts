/** Months 1 to 5 are Spring, 6 to 12 are Fall, matching the backend planning terms. */
export function currentTerm(today: Date = new Date()) {
  return `${today.getMonth() < 5 ? "Spring" : "Fall"} ${today.getFullYear()}`;
}
