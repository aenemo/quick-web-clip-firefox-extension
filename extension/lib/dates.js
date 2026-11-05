const pad = (n) => String(n).padStart(2, "0");

export function localDate(d = new Date()) {
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
}

export function normalisePublished(s) {
  if (typeof s !== "string" || s.trim() === "") return null;
  const text = s.trim();
  // A bare date has no time zone. Date.parse would read it as UTC and could
  // shift the day in a negative-offset zone, so keep it as written.
  const plain = /^(\d{4})-(\d{2})-(\d{2})$/.exec(text);
  if (plain) {
    const [y, m, d] = plain.slice(1).map(Number);
    const check = new Date(y, m - 1, d);
    const valid = check.getFullYear() === y && check.getMonth() === m - 1 && check.getDate() === d;
    return valid ? text : null;
  }
  const ms = Date.parse(text);
  if (Number.isNaN(ms)) return null;
  return localDate(new Date(ms));
}
