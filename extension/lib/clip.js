import { normaliseSettings, getDefaultDestination } from "./settings.js";
import { isClippable, classifyUrl } from "./classify.js";
import { normalisePublished } from "./dates.js";

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

function fail(tab, deps, message) {
  try {
    deps.setBadge(tab.id, "error");
    deps.notify(message);
  } catch {
    // Reporting a failure must never throw.
  }
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
      deps.notify(UNCLIPPABLE);
      return { status: "skipped", message: UNCLIPPABLE };
    }
    const dest =
      settings.destinations.find((d) => d.id === destinationId) ?? getDefaultDestination(settings);

    deps.setBadge(tab.id, "working");

    let extracted;
    try {
      extracted = await deps.extract(tab.id);
    } catch {
      return fail(tab, deps, EXTRACT_FAILED);
    }
    const { page = {}, ogType = null, bodyMarkdown = "" } = extracted ?? {};
    const url = page.url || tab.url;

    const request = {
      v: 1,
      action: "save",
      kind: classifyUrl(url, ogType),
      destination: { vaultPath: dest.vaultPath, subfolder: dest.subfolder },
      datePosition: settings.datePosition,
      clippedDate: deps.today(),
      page: {
        url,
        title: page.title ?? "",
        author: page.author ?? "",
        published: normalisePublished(page.published),
        siteName: page.siteName ?? "",
        description: page.description ?? "",
      },
      bodyMarkdown,
    };

    let reply;
    try {
      reply = await deps.sendNative(request);
    } catch (err) {
      return fail(tab, deps, errorMessage(err));
    }

    if (!reply || reply.ok !== true) return fail(tab, deps, errorMessage(reply ?? {}));

    if (reply.warning) {
      deps.setBadge(tab.id, "warning");
      deps.notify(reply.warning);
      return { status: "warning", message: reply.warning, path: reply.path };
    }
    deps.setBadge(tab.id, "ok");
    return { status: "ok", path: reply.path };
  } catch (err) {
    return fail(tab, deps, `Unexpected error: ${err?.message ?? err}`);
  }
}
