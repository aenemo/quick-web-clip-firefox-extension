import test from "node:test";
import assert from "node:assert/strict";
import { runClip, errorMessage } from "../extension/lib/clip.js";

const HELPER_MISSING = "Helper not found. Run install.bat in the helper folder.";

function makeDeps(over = {}) {
  const calls = { badge: [], notify: [], native: [], options: 0, extract: [] };
  const deps = {
    getSettings: async () => ({
      destinations: [
        { id: "a", label: "Work", vaultPath: "C:\\Work", subfolder: "Clippings", isDefault: true },
        { id: "b", label: "Home", vaultPath: "C:\\Home", subfolder: "Web", isDefault: false },
      ],
      datePosition: "end",
    }),
    extract: async (tabId) => {
      calls.extract.push(tabId);
      return {
        page: {
          url: "https://example.com/post",
          title: "A Post",
          author: "Ann",
          published: "2026-03-14T10:00:00Z",
          siteName: "Example",
          description: "Desc",
        },
        ogType: "article",
        bodyMarkdown: "Body",
      };
    },
    sendNative: async (msg) => {
      calls.native.push(msg);
      return { ok: true, path: "C:\\Work\\Clippings\\A Post 2026-11-06.md", kind: "article", transcript: "none", warning: null };
    },
    openOptions: async () => {
      calls.options++;
    },
    setBadge: (id, state) => calls.badge.push([id, state]),
    notify: (m) => calls.notify.push(m),
    today: () => "2026-11-06",
    ...over,
  };
  return { deps, calls };
}

const tab = { id: 7, url: "https://example.com/post" };

test("no destinations opens options", async () => {
  const { deps, calls } = makeDeps({ getSettings: async () => ({ destinations: [] }) });
  const r = await runClip({ tab }, deps);
  assert.equal(r.status, "skipped");
  assert.equal(calls.options, 1);
  assert.equal(calls.native.length, 0);
});

test("unclippable page notifies and skips", async () => {
  const { deps, calls } = makeDeps();
  const r = await runClip({ tab: { id: 1, url: "about:blank" } }, deps);
  assert.deepEqual(r, { status: "skipped", message: "This page can't be clipped" });
  assert.deepEqual(calls.notify, ["This page can't be clipped"]);
  assert.deepEqual(calls.badge, []);
  assert.equal(calls.extract.length, 0);
});

test("default destination request shape", async () => {
  const { deps, calls } = makeDeps();
  const r = await runClip({ tab }, deps);
  assert.deepEqual(calls.native, [
    {
      v: 1,
      action: "save",
      kind: "article",
      destination: { vaultPath: "C:\\Work", subfolder: "Clippings" },
      datePosition: "end",
      clippedDate: "2026-11-06",
      page: {
        url: "https://example.com/post",
        title: "A Post",
        author: "Ann",
        published: "2026-03-14",
        siteName: "Example",
        description: "Desc",
      },
      bodyMarkdown: "Body",
      attachments: [],
    },
  ]);
  assert.equal(r.status, "ok");
  assert.equal(r.path, "C:\\Work\\Clippings\\A Post 2026-11-06.md");
  assert.deepEqual(calls.badge, [[7, "working"], [7, "ok"]]);
  assert.deepEqual(calls.notify, []);
});

test("menu destination used", async () => {
  const { deps, calls } = makeDeps();
  await runClip({ tab, destinationId: "b" }, deps);
  assert.deepEqual(calls.native[0].destination, { vaultPath: "C:\\Home", subfolder: "Web" });
});

test("unknown destination falls back to default", async () => {
  const { deps, calls } = makeDeps();
  await runClip({ tab, destinationId: "zzz" }, deps);
  assert.deepEqual(calls.native[0].destination, { vaultPath: "C:\\Work", subfolder: "Clippings" });
});

test("youtube classified as video", async () => {
  const url = "https://www.youtube.com/watch?v=abc";
  const { deps, calls } = makeDeps({
    extract: async () => ({ page: { url, title: "V" }, ogType: null, bodyMarkdown: "" }),
  });
  await runClip({ tab: { id: 2, url } }, deps);
  assert.equal(calls.native[0].kind, "video");
});

test("helper missing message", async () => {
  const { deps, calls } = makeDeps({
    sendNative: async () => {
      throw new Error("No such native application");
    },
  });
  const r = await runClip({ tab }, deps);
  assert.deepEqual(r, { status: "error", message: HELPER_MISSING });
  assert.deepEqual(calls.badge.at(-1), [7, "error"]);
  assert.deepEqual(calls.notify, [HELPER_MISSING]);
});

test("reply error uses helper message", async () => {
  const { deps, calls } = makeDeps({
    sendNative: async () => ({ ok: false, error: "vault_not_found", message: "Folder not found: C:\\Work" }),
  });
  const r = await runClip({ tab }, deps);
  assert.deepEqual(r, { status: "error", message: "Folder not found: C:\\Work" });
  assert.deepEqual(calls.badge.at(-1), [7, "error"]);
  assert.deepEqual(calls.notify, ["Folder not found: C:\\Work"]);
});

test("warning path", async () => {
  const w = "Saved without transcript: yt-dlp not installed";
  const { deps, calls } = makeDeps({
    sendNative: async () => ({ ok: true, path: "C:\\x.md", kind: "video", transcript: "none", warning: w }),
  });
  const r = await runClip({ tab }, deps);
  assert.deepEqual(r, { status: "warning", message: w, path: "C:\\x.md" });
  assert.deepEqual(calls.badge.at(-1), [7, "warning"]);
  assert.deepEqual(calls.notify, [w]);
});

test("extract failure", async () => {
  const { deps, calls } = makeDeps({
    extract: async () => {
      throw new Error("injection failed");
    },
  });
  const r = await runClip({ tab }, deps);
  assert.deepEqual(r, { status: "error", message: "Could not read this page" });
  assert.equal(calls.native.length, 0);
  assert.deepEqual(calls.badge.at(-1), [7, "error"]);
  assert.deepEqual(calls.notify, ["Could not read this page"]);
});

test("unexpected exception becomes error and never throws", async () => {
  const { deps, calls } = makeDeps({
    getSettings: async () => {
      throw new Error("storage exploded");
    },
  });
  const r = await runClip({ tab }, deps);
  assert.equal(r.status, "error");
  assert.ok(r.message);
  assert.deepEqual(calls.badge.at(-1), [7, "error"]);
  assert.deepEqual(calls.notify, [r.message]);
});

test("errorMessage maps reply and thrown cases", () => {
  assert.equal(errorMessage(new Error("x")), HELPER_MISSING);
  assert.equal(errorMessage({ ok: false, message: "Refused" }), "Refused");
});

test("any native rejection maps to helper missing", async () => {
  const { deps, calls } = makeDeps({
    sendNative: async () => {
      throw { message: "No such native application" };
    },
  });
  const r = await runClip({ tab }, deps);
  assert.deepEqual(r, { status: "error", message: HELPER_MISSING });
  assert.deepEqual(calls.notify, [HELPER_MISSING]);
});

test("throwing setBadge does not change a successful result", async () => {
  const { deps, calls } = makeDeps({
    setBadge: () => {
      throw new Error("badge broke");
    },
  });
  const r = await runClip({ tab }, deps);
  assert.equal(r.status, "ok");
  assert.equal(calls.native.length, 1);
});

test("throwing setBadge in an error path still notifies", async () => {
  const { deps, calls } = makeDeps({
    setBadge: () => {
      throw new Error("badge broke");
    },
    sendNative: async () => ({ ok: false, message: "Folder not found: X" }),
  });
  const r = await runClip({ tab }, deps);
  assert.deepEqual(r, { status: "error", message: "Folder not found: X" });
  assert.deepEqual(calls.notify, ["Folder not found: X"]);
});

test("throwing notify does not change a warning result", async () => {
  const w = "Saved without transcript: yt-dlp not installed";
  const { deps, calls } = makeDeps({
    notify: () => {
      throw new Error("notify broke");
    },
    sendNative: async () => ({ ok: true, path: "x.md", warning: w }),
  });
  const r = await runClip({ tab }, deps);
  assert.equal(r.status, "warning");
  assert.deepEqual(calls.badge.at(-1), [7, "warning"]);
});

test("stale canonical on a video tab uses the live tab URL", async () => {
  const tabUrl = "https://www.youtube.com/watch?v=second";
  const stale = "https://www.youtube.com/watch?v=first";
  const { deps, calls } = makeDeps({
    extract: async () => ({ page: { url: stale, title: "V" }, ogType: null, bodyMarkdown: "" }),
  });
  await runClip({ tab: { id: 3, url: tabUrl } }, deps);
  assert.equal(calls.native[0].kind, "video");
  assert.equal(calls.native[0].page.url, tabUrl);
});

test("article page keeps its canonical URL", async () => {
  const canonical = "https://example.com/canonical-post";
  const { deps, calls } = makeDeps({
    extract: async () => ({ page: { url: canonical, title: "P" }, ogType: "article", bodyMarkdown: "" }),
  });
  await runClip({ tab: { id: 4, url: "https://example.com/post?utm=1" } }, deps);
  assert.equal(calls.native[0].kind, "article");
  assert.equal(calls.native[0].page.url, canonical);
});

test("extracted images are passed to the helper", async () => {
  const attachments = [{ token: "qwc-attachment:0", mime: "image/jpeg", data: "AAAA" }];
  const { deps, calls } = makeDeps({
    extract: async () => ({ page: { url: "https://teams.cloud.microsoft/", title: "Chat" }, bodyMarkdown: "x", attachments }),
  });
  await runClip({ tab: { id: 5, url: "https://teams.cloud.microsoft/" } }, deps);
  assert.deepEqual(calls.native[0].attachments, attachments);
});

test("a selection is saved as an article, even on a video page", async () => {
  const tabUrl = "https://www.youtube.com/watch?v=abc123";
  const { deps, calls } = makeDeps({
    extract: async () => ({ page: { url: tabUrl, title: "V" }, ogType: "video.other", bodyMarkdown: "picked", selection: true }),
  });
  await runClip({ tab: { id: 6, url: tabUrl } }, deps);
  assert.equal(calls.native[0].kind, "article");
  assert.equal(calls.native[0].bodyMarkdown, "picked");
});

test("without a selection a video page is still a video clip", async () => {
  const tabUrl = "https://www.youtube.com/watch?v=abc123";
  const { deps, calls } = makeDeps({
    extract: async () => ({ page: { url: tabUrl, title: "V" }, ogType: "video.other", bodyMarkdown: "", selection: false }),
  });
  await runClip({ tab: { id: 6, url: tabUrl } }, deps);
  assert.equal(calls.native[0].kind, "video");
});
