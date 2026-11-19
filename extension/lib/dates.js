const pad = (n) => String(n).padStart(2, "0");

export function localDate(d = new Date()) {
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
}

// "14:05" (24-hour) or "2:05 pm" (12-hour).
export function localTime(d = new Date(), format = "12h") {
  const h = d.getHours();
  const m = pad(d.getMinutes());
  if (format === "24h") return `${pad(h)}:${m}`;
  return `${h % 12 || 12}:${m} ${h < 12 ? "am" : "pm"}`;
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
