// Image handling for clips. Injected before extract.js; defines globalThis.__qwcImages.
// The helpers are covered by the Node tests through the same global.
(() => {
  // Microsoft Teams chat images are shown through blob: URLs that only exist inside the tab.
  // A loaded image keeps its original URL in data-orig-src; one not yet loaded only has its
  // media (AMS) object ID, in itemid or in its id as "x_<object id>".
  const AMS_ID = /^0-[a-z0-9]+-[a-z0-9]+-[0-9a-f]{16,}$/i;
  const DEFAULT_GATEWAY = "as-prod.asyncgw.teams.microsoft.com";
  const GATEWAY_HOST = /^[a-z0-9-]+\.asyncgw\.teams\.microsoft\.com$/i;
  const TOKEN_PREFIX = "qwc-attachment:";
  const LOCAL_ATTR = "data-qwc-local";
  const MAX_IMAGE_BYTES = 15 * 1024 * 1024;
  const MAX_TOTAL_BYTES = 40 * 1024 * 1024;
  const MAX_IMAGES = 100;

  const isAmsId = (id) => typeof id === "string" && AMS_ID.test(id);

  // The gateway host Teams itself fetched images from, or a default that routes any region.
  function pickGatewayHost(resourceUrls) {
    for (const u of resourceUrls || []) {
      try {
        const host = new URL(u).host;
        if (GATEWAY_HOST.test(host)) return host;
      } catch {
        // not a URL
      }
    }
    return DEFAULT_GATEWAY;
  }

  const amsImageUrl = (id, host) => `https://${host}/v1/objects/${encodeURIComponent(id)}/views/imgo`;

  const isAmsImageUrl = (src) => {
    try {
      const u = new URL(src);
      return u.protocol === "https:" && GATEWAY_HOST.test(u.host) && u.pathname.startsWith("/v1/objects/");
    } catch {
      return false;
    }
  };

  // The original online URL of a Teams chat image, or null for any other image.
  function teamsImageUrl(img, host) {
    const orig = img.getAttribute("data-orig-src");
    if (orig && isAmsImageUrl(orig)) return orig;
    if (!/AMSImage/i.test(img.getAttribute("itemtype") || "")) return null;
    const itemid = img.getAttribute("itemid");
    if (isAmsId(itemid)) return amsImageUrl(itemid, host);
    const id = (img.getAttribute("id") || "").replace(/^x_/, "");
    if (isAmsId(id)) return amsImageUrl(id, host);
    return null;
  }

  // Teams profile pictures load only while signed in, so they would be broken in a note.
  const isTeamsAvatar = (src) => {
    try {
      const u = new URL(src);
      return /(^|\.)teams\.(cloud\.)?microsoft(\.com)?$/i.test(u.host) && /\/profilepicture/i.test(u.pathname);
    } catch {
      return false;
    }
  };

  // Point Teams images in a cloned document at their original URL, before Readability runs.
  // A loaded copy (blob: URL) is remembered so it can be read without another download.
  // Teams profile pictures are dropped.
  function resolveTeamsImages(doc, resourceUrls) {
    const host = pickGatewayHost(resourceUrls);
    for (const img of doc.querySelectorAll("img")) {
      if (isTeamsAvatar(img.getAttribute("src") || "")) {
        img.remove();
        continue;
      }
      const url = teamsImageUrl(img, host);
      if (!url) continue;
      const src = img.getAttribute("src") || "";
      if (src.startsWith("blob:")) img.setAttribute(LOCAL_ATTR, src);
      img.setAttribute("src", url);
    }
  }

  function blobToBase64(blob) {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onload = () => {
        const s = String(reader.result);
        resolve(s.slice(s.indexOf(",") + 1));
      };
      reader.onerror = () => reject(reader.error || new Error("read failed"));
      reader.readAsDataURL(blob);
    });
  }

  // Returns { mime, data } for an image URL, or null. Never throws.
  async function download(url, fetchFn, budget) {
    try {
      const res = await fetchFn(url, { credentials: "include" });
      if (!res.ok) return null;
      const blob = await res.blob();
      const mime = String(blob.type || res.headers.get("content-type") || "")
        .split(";")[0]
        .trim()
        .toLowerCase();
      if (!mime.startsWith("image/") || blob.size === 0) return null;
      if (blob.size > MAX_IMAGE_BYTES || blob.size > budget) return null;
      const data = await blobToBase64(blob);
      return data ? { mime, data, size: blob.size } : null;
    } catch {
      return null;
    }
  }

  // Download images that only the signed-in tab can reach (Teams images and blob: URLs),
  // replace their src with a token the helper swaps for the saved file, and link each
  // Teams image to its original URL. Returns the attachments for the save request.
  async function collectAttachments(container, fetchFns) {
    const fetchers = (Array.isArray(fetchFns) ? fetchFns : [fetchFns]).filter((f) => typeof f === "function");
    const attachments = [];
    const byUrl = new Map();
    let total = 0;
    for (const img of container.querySelectorAll("img[src]")) {
      const src = img.getAttribute("src");
      const local = img.getAttribute(LOCAL_ATTR);
      img.removeAttribute(LOCAL_ATTR);
      const ams = isAmsImageUrl(src);
      if (!ams && !src.startsWith("blob:")) continue;

      if (ams && !img.closest("a[href]")) {
        const a = container.ownerDocument.createElement("a");
        a.setAttribute("href", src);
        img.replaceWith(a);
        a.appendChild(img);
      }

      if (byUrl.has(src)) {
        img.setAttribute("src", byUrl.get(src));
        continue;
      }
      let got = null;
      if (attachments.length < MAX_IMAGES) {
        const sources = [local, src].filter((u) => u && (u.startsWith("blob:") || isAmsImageUrl(u)));
        for (const url of sources) {
          for (const f of fetchers) {
            got = await download(url, f, MAX_TOTAL_BYTES - total);
            if (got) break;
          }
          if (got) break;
        }
      }
      if (got) {
        const token = TOKEN_PREFIX + attachments.length;
        attachments.push({ token, mime: got.mime, data: got.data });
        total += got.size;
        byUrl.set(src, token);
        img.setAttribute("src", token);
      } else if (!ams) {
        img.remove(); // a blob: URL means nothing outside this tab
      }
    }
    return attachments;
  }

  globalThis.__qwcImages = {
    isAmsId,
    pickGatewayHost,
    amsImageUrl,
    isAmsImageUrl,
    isTeamsAvatar,
    teamsImageUrl,
    resolveTeamsImages,
    collectAttachments,
  };
})();
