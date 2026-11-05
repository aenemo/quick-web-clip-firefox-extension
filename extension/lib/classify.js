const isHost = (u, domain) => u.hostname === domain || u.hostname.endsWith("." + domain);

const VIDEO_PATTERNS = [
  (u) => u.hostname === "m.youtube.com",
  (u) => isHost(u, "youtube.com") && u.pathname === "/watch",
  (u) => isHost(u, "youtube.com") && /^\/(shorts|live)\/./.test(u.pathname),
  (u) => u.hostname === "youtu.be" && u.pathname.length > 1,
  (u) => isHost(u, "vimeo.com") && /^\/(video\/)?\d+(\/|$)/.test(u.pathname),
  (u) => isHost(u, "dailymotion.com") && u.pathname.startsWith("/video/"),
  (u) => isHost(u, "ted.com") && u.pathname.startsWith("/talks/"),
];

export function isClippable(url) {
  let u;
  try {
    u = new URL(url);
  } catch {
    return false;
  }
  if (!["http:", "https:", "file:"].includes(u.protocol)) return false;
  if (u.hostname === "addons.mozilla.org") return false;
  if (u.pathname.toLowerCase().endsWith(".pdf")) return false;
  return true;
}

export function classifyUrl(url, ogType = null) {
  if (ogType?.startsWith("video")) return "video";
  let u;
  try {
    u = new URL(url);
  } catch {
    return "article";
  }
  return VIDEO_PATTERNS.some((matches) => matches(u)) ? "video" : "article";
}
