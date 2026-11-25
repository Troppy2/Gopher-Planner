/** Months 1 to 5 are Spring, 6 to 12 are Fall, matching the backend planning terms. */
export function currentTerm(today: Date = new Date()) {
  return `${today.getMonth() < 5 ? "Spring" : "Fall"} ${today.getFullYear()}`;
}

/** The next `count` Spring and Fall terms after the current one, for graduation targets. */
export function upcomingTerms(count = 12, today: Date = new Date()) {
  let season = today.getMonth() < 5 ? "Spring" : "Fall";
  let year = today.getFullYear();
  const terms: string[] = [];
  while (terms.length < count) {
    if (season === "Spring") season = "Fall";
    else {
      season = "Spring";
      year += 1;
    }
    terms.push(`${season} ${year}`);
  }
  return terms;
}
