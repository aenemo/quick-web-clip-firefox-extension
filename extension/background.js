import "./compat.js";
import { runClip } from "./lib/clip.js";
import { buildMenuModel, normaliseSettings } from "./lib/settings.js";

const NATIVE_HOST = "quick_web_clip";
const PARENT_MENU_ID = "qwc-save-to";
const DEST_PREFIX = "dest:";

const BADGES = {
  working: { text: "...", color: "#1565c0" },
  ok: { text: "OK", color: "#2e7d32" },
  warning: { text: "!", color: "#f9a825" },
  error: { text: "ERR", color: "#c62828" },
};

const badgeTimers = new Map();

async function setBadge(tabId, state) {
  const b = BADGES[state];
  // Any state change cancels a pending OK-clear for this tab.
  clearTimeout(badgeTimers.get(tabId));
  badgeTimers.delete(tabId);
  await browser.action.setBadgeText({ tabId, text: b.text });
  await browser.action.setBadgeBackgroundColor({ tabId, color: b.color });
  if (state === "ok") {
    badgeTimers.set(
      tabId,
      setTimeout(() => {
        badgeTimers.delete(tabId);
        browser.action.setBadgeText({ tabId, text: "" }).catch(() => {});
      }, 2000),
    );
  }
}

async function extract(tabId) {
  await browser.scripting.executeScript({
    target: { tabId },
    files: [
      "vendor/Readability.js",
      "vendor/turndown.js",
      "vendor/turndown-plugin-gfm.js",
      "content/images.js",
      "content/teams.js",
      "content/extract.js",
    ],
  });
  const results = await browser.scripting.executeScript({
    target: { tabId },
    func: () => window.__qwcExtract(),
  });
  return results[0].result;
}

const deps = {
  getSettings: () => browser.storage.local.get(null),
  openOptions: () => browser.runtime.openOptionsPage(),
  extract,
  sendNative: (msg) => browser.runtime.sendNativeMessage(NATIVE_HOST, msg),
  setBadge,
  notify: (message) =>
    browser.notifications.create({
      type: "basic",
      title: "Quick Web Clip",
      message,
      iconUrl: "icons/icon-96.png",
    }),
  now: () => new Date(),
};

function clip(tab, destinationId = null) {
  if (!tab || tab.id == null) return Promise.resolve();
  return runClip({ tab, destinationId }, deps);
}

async function activeTab() {
  const [tab] = await browser.tabs.query({ active: true, currentWindow: true });
  return tab;
}

function createMenu(props) {
  return new Promise((resolve) => {
    browser.menus.create(props, () => {
      void browser.runtime.lastError; // read so a failure is never reported as unchecked
      resolve();
    });
  });
}

async function doRebuild() {
  await browser.menus.removeAll();
  const settings = normaliseSettings(await browser.storage.local.get(null));
  if (settings.destinations.length === 0) return;
  await createMenu({ id: PARENT_MENU_ID, title: "Save to", contexts: ["page", "selection", "image", "action"] });
  for (const item of buildMenuModel(settings)) {
    await createMenu({
      id: item.id,
      parentId: PARENT_MENU_ID,
      title: item.title,
      contexts: ["page", "selection", "image", "action"],
    });
  }
}

// Serialise rebuilds so concurrent triggers cannot interleave and duplicate ids.
let menuBuild = Promise.resolve();
const rebuildMenus = () => (menuBuild = menuBuild.then(doRebuild, doRebuild));

browser.action.onClicked.addListener((tab) => clip(tab));

browser.commands.onCommand.addListener(async (name) => {
  if (name !== "clip-default") return;
  clip(await activeTab());
});

browser.menus.onClicked.addListener((info, tab) => {
  const id = String(info.menuItemId);
  if (!id.startsWith(DEST_PREFIX)) return;
  clip(tab, id.slice(DEST_PREFIX.length));
});

browser.storage.onChanged.addListener(() => {
  rebuildMenus().catch(() => {});
});

rebuildMenus().catch(() => {});
