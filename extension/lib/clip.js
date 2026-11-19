import { normaliseSettings, getDefaultDestination } from "./settings.js";
import { isClippable, classifyUrl } from "./classify.js";
import { localDate, localTime, normalisePublished } from "./dates.js";

const HELPER_MISSING = "Helper not found. Run install.bat in the helper folder.";
const EXTRACT_FAILED = "Could not read this page";
const UNCLIPPABLE = "This page can't be clipped";
const GENERIC_FAILURE = "Could not save the clip";

// A thrown error (no reply) means the native host could not be reached.
// A reply carries the helper's own formatted message.
export function errorMessage(errOrReply) {
  if (errOrReply instanceof Error || errOrReply == null) return HELPER_MISSING;
  if (typeof errOrReply === "object" && typeof errOrReply.message === "string" && errOrReply.message) {
    return errOrReply.message;
  }
  return GENERIC_FAILURE;
}

function safe(fn) {
  try {
    fn();
  } catch {
    // UI feedback must never change the clip result.
  }
}

function fail(tab, deps, message) {
  safe(() => deps.setBadge(tab.id, "error"));
  safe(() => deps.notify(message));
  return { status: "error", message };
}

export async function runClip({ tab, destinationId = null }, deps) {
  try {
    const settings = normaliseSettings(await deps.getSettings());
    if (settings.destinations.length === 0) {
      await deps.openOptions();
      return { status: "skipped" };
    }
    if (!isClippable(tab.url)) {
      safe(() => deps.notify(UNCLIPPABLE));
      return { status: "skipped", message: UNCLIPPABLE };
    }
    const dest =
      settings.destinations.find((d) => d.id === destinationId) ?? getDefaultDestination(settings);

    safe(() => deps.setBadge(tab.id, "working"));

    let extracted;
    try {
      extracted = await deps.extract(tab.id);
    } catch {
      return fail(tab, deps, EXTRACT_FAILED);
    }
    const { page = {}, ogType = null, bodyMarkdown = "", attachments = [], selection = false } = extracted ?? {};
    // The canonical link can lag after in-page navigation (YouTube), so a video tab URL wins.
    const url = classifyUrl(tab.url, null) === "video" ? tab.url : page.url || tab.url;

    const now = deps.now();
    const request = {
      v: 1,
      action: "save",
      // A selection is saved as it is, even on a video page.
      kind: selection === true ? "article" : classifyUrl(url, ogType),
      destination: { vaultPath: dest.vaultPath, subfolder: dest.subfolder },
      datePosition: settings.datePosition,
      clippedDate: localDate(now),
      clippedTime: localTime(now, settings.timeFormat),
      page: {
        url,
        title: page.title ?? "",
        author: page.author ?? "",
        published: normalisePublished(page.published),
        siteName: page.siteName ?? "",
        description: page.description ?? "",
      },
      bodyMarkdown,
      attachments: Array.isArray(attachments) ? attachments : [],
    };

    let reply;
    try {
      reply = await deps.sendNative(request);
    } catch {
      return fail(tab, deps, HELPER_MISSING);
    }

    if (!reply || reply.ok !== true) return fail(tab, deps, errorMessage(reply ?? {}));

    if (reply.warning) {
      safe(() => deps.setBadge(tab.id, "warning"));
      safe(() => deps.notify(reply.warning));
      return { status: "warning", message: reply.warning, path: reply.path };
    }
    safe(() => deps.setBadge(tab.id, "ok"));
    return { status: "ok", path: reply.path };
  } catch (err) {
    return fail(tab, deps, `Unexpected error: ${err?.message ?? err}`);
  }
}
