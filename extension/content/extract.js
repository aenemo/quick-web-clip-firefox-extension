// Injected after the vendored Readability, turndown and turndown-plugin-gfm.
// Defines window.__qwcExtract, which returns the page metadata and the body as Markdown.
(() => {
  const meta = (sel) => {
    const el = document.querySelector(sel);
    const v = el && el.getAttribute("content");
    return v ? v.trim() : "";
  };

  const abs = (v) => {
    try {
      return new URL(v, document.baseURI).href;
    } catch {
      return v;
    }
  };

  const jsonLd = () => {
    const out = { author: "", published: "" };
    for (const s of document.querySelectorAll('script[type="application/ld+json"]')) {
      let data;
      try {
        data = JSON.parse(s.textContent);
      } catch {
        continue;
      }
      const nodes = [];
      const walk = (n) => {
        if (Array.isArray(n)) n.forEach(walk);
        else if (n && typeof n === "object") {
          nodes.push(n);
          if (n["@graph"]) walk(n["@graph"]);
        }
      };
      walk(data);
      for (const n of nodes) {
        if (!out.published && typeof n.datePublished === "string") out.published = n.datePublished;
        if (!out.author && n.author) {
          const a = Array.isArray(n.author) ? n.author[0] : n.author;
          const name = typeof a === "string" ? a : a && a.name;
          if (typeof name === "string") out.author = name.trim();
        }
      }
    }
    return out;
  };

  // Fetch as the page would first (Firefox content.fetch), so Teams images use the tab's
  // sign-in and its blob: URLs; then the content script's own fetch.
  const pageFetchers = [];
  if (typeof content !== "undefined" && content && typeof content.fetch === "function") {
    pageFetchers.push(content.fetch.bind(content));
  }
  pageFetchers.push(fetch);

  // A copy of what the user has selected, or null when nothing (or only whitespace) is selected.
  const selectedContent = () => {
    const sel = window.getSelection();
    if (!sel || sel.isCollapsed || sel.rangeCount === 0) return null;
    const holder = document.createElement("div");
    for (let i = 0; i < sel.rangeCount; i++) holder.appendChild(sel.getRangeAt(i).cloneContents());
    return holder.textContent.trim() || holder.querySelector("img") ? holder : null;
  };

  const resolveImages = (root) => {
    try {
      globalThis.__qwcImages.resolveTeamsImages(root, performance.getEntriesByType("resource").map((e) => e.name));
    } catch {
      // Images keep their page URLs.
    }
  };

  window.__qwcExtract = async () => {
    const images = globalThis.__qwcImages;
    let article = null;
    let html;
    const selection = selectedContent();
    if (selection) {
      // Only the selection is clipped, as it is: no Readability.
      resolveImages(selection);
      if (globalThis.__qwcTeams && globalThis.__qwcTeams.isTeamsHost(location.host)) {
        try {
          globalThis.__qwcTeams.tidyTeamsChat(selection);
        } catch {
          // Clip the selection untidied.
        }
      }
      html = selection.innerHTML;
    } else {
      const prepared = document.cloneNode(true);
      resolveImages(prepared);
      try {
        article = new Readability(prepared.cloneNode(true)).parse();
      } catch {
        article = null;
      }
      html = article && article.content && article.content.trim() ? article.content : prepared.body.innerHTML;
    }

    // Parse into an inert document (no script execution, no resource loading).
    const container = new DOMParser().parseFromString(html, "text/html").body;
    for (const img of container.querySelectorAll("img[src]")) img.setAttribute("src", abs(img.getAttribute("src")));
    for (const a of container.querySelectorAll("a[href]")) a.setAttribute("href", abs(a.getAttribute("href")));

    let attachments = [];
    try {
      attachments = await images.collectAttachments(container, pageFetchers);
    } catch {
      attachments = [];
    }

    const td = new TurndownService({ headingStyle: "atx", codeBlockStyle: "fenced", bulletListMarker: "-" });
    td.use(turndownPluginGfm.gfm);
    const bodyMarkdown = td.turndown(container.innerHTML);

    const ld = jsonLd();
    const canonical = document.querySelector("link[rel=canonical]");
    const url = (canonical && canonical.href) || location.href;

    const page = {
      url,
      title: (article && article.title) || meta('meta[property="og:title"]') || document.title || "",
      author:
        (article && article.byline) ||
        meta('meta[name="author"]') ||
        meta('meta[property="article:author"]') ||
        ld.author,
      published:
        (article && article.publishedTime) ||
        meta('meta[property="article:published_time"]') ||
        ld.published,
      siteName: (article && article.siteName) || meta('meta[property="og:site_name"]'),
      description:
        (article && article.excerpt) || meta('meta[property="og:description"]') || meta('meta[name="description"]'),
    };

    return {
      page,
      ogType: meta('meta[property="og:type"]') || null,
      bodyMarkdown,
      attachments,
      selection: Boolean(selection),
    };
  };
})();
