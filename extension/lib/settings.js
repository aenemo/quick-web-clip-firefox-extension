export const DEFAULT_SETTINGS = { destinations: [], datePosition: "end", timeFormat: "12h" };

const DATE_POSITIONS = ["end", "start", "none"];
const TIME_FORMATS = ["12h", "24h"];

// Exactly one default: prefer preferId, else the first flagged, else the first.
function withSingleDefault(destinations, preferId = null) {
  let chosen = preferId !== null ? destinations.findIndex((d) => d.id === preferId) : -1;
  if (chosen < 0) chosen = destinations.findIndex((d) => d.isDefault);
  if (chosen < 0) chosen = 0;
  return destinations.map((d, i) => ({ ...d, isDefault: i === chosen }));
}

export function normaliseSettings(raw) {
  const src = raw && typeof raw === "object" ? raw : {};
  const list = Array.isArray(src.destinations) ? src.destinations : [];
  const destinations = withSingleDefault(
    list
      .filter((d) => d && typeof d === "object" && d.id != null)
      .map((d) => ({
      id: String(d.id),
      label: d.label ?? "",
      vaultPath: d.vaultPath ?? "",
      subfolder: d.subfolder ?? "",
      isDefault: Boolean(d.isDefault),
    })),
  );
  const datePosition = DATE_POSITIONS.includes(src.datePosition) ? src.datePosition : "end";
  const timeFormat = TIME_FORMATS.includes(src.timeFormat) ? src.timeFormat : "12h";
  return { destinations, datePosition, timeFormat };
}

export function validateDestination(d) {
  const errors = [];
  const label = (d?.label ?? "").trim();
  const vaultPath = (d?.vaultPath ?? "").trim();
  if (!label) errors.push("Label is required");
  if (!vaultPath) {
    errors.push("Vault folder is required");
  } else if (!/^[A-Za-z]:\\|^\\\\/.test(vaultPath)) {
    errors.push("Vault folder must be a full path");
  }
  return errors;
}

export function getDefaultDestination(s) {
  return s.destinations.find((d) => d.isDefault) ?? null;
}

export function setDefault(s, id) {
  return { ...s, destinations: withSingleDefault(s.destinations, id) };
}

export function removeDestination(s, id) {
  const rest = s.destinations.filter((d) => d.id !== id);
  return { ...s, destinations: rest.length ? withSingleDefault(rest) : [] };
}

export function upsertDestination(s, d) {
  const i = s.destinations.findIndex((x) => x.id === d.id);
  const list = i < 0 ? [...s.destinations, { ...d }] : s.destinations.map((x, j) => (j === i ? { ...d } : x));
  return { ...s, destinations: withSingleDefault(list, d.isDefault ? d.id : null) };
}

export function moveDestination(s, id, delta) {
  const from = s.destinations.findIndex((d) => d.id === id);
  if (from < 0) return { ...s, destinations: [...s.destinations] };
  const to = Math.max(0, Math.min(s.destinations.length - 1, from + delta));
  const list = [...s.destinations];
  const [item] = list.splice(from, 1);
  list.splice(to, 0, item);
  return { ...s, destinations: list };
}

export function buildMenuModel(s) {
  return s.destinations.map((d) => ({
    id: "dest:" + d.id,
    title: d.isDefault ? `${d.label} (default)` : d.label,
  }));
}
