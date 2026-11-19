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

  window.__qwcExtract = async () => {
    const images = globalThis.__qwcImages;
    const prepared = document.cloneNode(true);
    try {
      images.resolveTeamsImages(prepared, performance.getEntriesByType("resource").map((e) => e.name));
    } catch {
      // Images keep their page URLs.
    }

    let article = null;
    try {
      article = new Readability(prepared.cloneNode(true)).parse();
    } catch {
      article = null;
    }

    const html = article && article.content && article.content.trim() ? article.content : prepared.body.innerHTML;

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

    return { page, ogType: meta('meta[property="og:type"]') || null, bodyMarkdown, attachments };
  };
})();
