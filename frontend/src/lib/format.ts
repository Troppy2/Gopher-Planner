export const plural = (n: number, one: string, many = one + "s") => `${n} ${n === 1 ? one : many}`;
export const credits = (n: number) => plural(n, "credit");
export const initial = (name: string) => (name.trim().charAt(0) || "?").toUpperCase();
