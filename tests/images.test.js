import test from "node:test";
import assert from "node:assert/strict";

// images.js is a classic content script: loading it defines globalThis.__qwcImages.
await import("../extension/content/images.js");
const images = globalThis.__qwcImages;

const ID = "0-sau-d1-0857ec2277af3f3b5876d79e5986896e";

test("isAmsId accepts Teams media IDs only", () => {
  assert.equal(images.isAmsId(ID), true);
  assert.equal(images.isAmsId("0-eau-d1-ef36c113f42eb2ddc18e09c1f4d91133"), true);
  assert.equal(images.isAmsId("abc"), false);
  assert.equal(images.isAmsId("0-sau-d1-../../x"), false);
  assert.equal(images.isAmsId(null), false);
});

test("pickGatewayHost uses the host Teams fetched from", () => {
  const urls = [
    "https://res.cdn.office.net/x.png",
    "not a url",
    "https://au-prod.asyncgw.teams.microsoft.com/v1/objects/x/views/imgo",
  ];
  assert.equal(images.pickGatewayHost(urls), "au-prod.asyncgw.teams.microsoft.com");
});

test("pickGatewayHost falls back to a default gateway", () => {
  assert.equal(images.pickGatewayHost([]), "as-prod.asyncgw.teams.microsoft.com");
  assert.equal(images.pickGatewayHost(["https://evil.example/asyncgw.teams.microsoft.com"]), "as-prod.asyncgw.teams.microsoft.com");
});

test("amsImageUrl builds the original image URL", () => {
  assert.equal(
    images.amsImageUrl(ID, "au-prod.asyncgw.teams.microsoft.com"),
    `https://au-prod.asyncgw.teams.microsoft.com/v1/objects/${ID}/views/imgo`,
  );
});

test("isAmsImageUrl recognises gateway object URLs", () => {
  assert.equal(images.isAmsImageUrl(`https://au-prod.asyncgw.teams.microsoft.com/v1/objects/${ID}/views/imgo`), true);
  assert.equal(images.isAmsImageUrl("blob:https://teams.cloud.microsoft/515bf6f9"), false);
  assert.equal(images.isAmsImageUrl("https://example.com/v1/objects/x"), false);
});

// Minimal stand-ins for the DOM pieces the image code touches.
class FakeEl {
  constructor(tag, attrs = {}) {
    this.tagName = tag.toUpperCase();
    this.attrs = { ...attrs };
    this.parent = null;
    this.children = [];
  }
  getAttribute(n) {
    return n in this.attrs ? this.attrs[n] : null;
  }
  setAttribute(n, v) {
    this.attrs[n] = String(v);
  }
  removeAttribute(n) {
    delete this.attrs[n];
  }
  appendChild(c) {
    c.parent = this;
    this.children.push(c);
  }
  replaceWith(other) {
    const i = this.parent.children.indexOf(this);
    this.parent.children[i] = other;
    other.parent = this.parent;
    this.parent = null;
  }
  remove() {
    this.parent.children.splice(this.parent.children.indexOf(this), 1);
    this.parent = null;
  }
  closest(sel) {
    for (let e = this; e; e = e.parent) if (sel === "a[href]" && e.tagName === "A" && "href" in e.attrs) return e;
    return null;
  }
  all() {
    return this.children.flatMap((c) => [c, ...c.all()]);
  }
  querySelectorAll(sel) {
    const imgs = this.all().filter((e) => e.tagName === "IMG");
    if (sel === "img[src]") return imgs.filter((e) => "src" in e.attrs);
    return imgs;
  }
}

function makeContainer(imgs) {
  const root = new FakeEl("body");
  root.ownerDocument = { createElement: (t) => new FakeEl(t) };
  for (const i of imgs) root.appendChild(i);
  return root;
}

globalThis.FileReader ??= class {
  readAsDataURL(blob) {
    blob.arrayBuffer().then((b) => {
      this.result = `data:${blob.type};base64,` + Buffer.from(b).toString("base64");
      this.onload();
    });
  }
};

const okFetch = (map) => async (url) => {
  if (!(url in map)) throw new TypeError("NetworkError");
  return new Response(new Blob([map[url]], { type: "image/jpeg" }), { status: 200 });
};

const ORIG = `https://au-prod.asyncgw.teams.microsoft.com/v1/objects/${ID}/views/imgo`;

test("teamsImageUrl reads a loaded image's data-orig-src", () => {
  const img = new FakeEl("img", { src: "blob:https://teams.cloud.microsoft/1", "data-orig-src": ORIG, itemtype: "http://schema.skype.com/AMSImage" });
  assert.equal(images.teamsImageUrl(img, "x"), ORIG);
});

test("teamsImageUrl builds the URL for an image not yet loaded", () => {
  const host = "au-prod.asyncgw.teams.microsoft.com";
  const byItemId = new FakeEl("img", { itemid: ID, itemtype: "http://schema.skype.com/AMSImage" });
  const byId = new FakeEl("img", { id: `x_${ID}`, itemtype: "http://schema.skype.com/AMSImage" });
  assert.equal(images.teamsImageUrl(byItemId, host), ORIG);
  assert.equal(images.teamsImageUrl(byId, host), ORIG);
});

test("teamsImageUrl ignores emoji and ordinary images", () => {
  assert.equal(images.teamsImageUrl(new FakeEl("img", { itemid: "yes-tone1", itemtype: "http://schema.skype.com/Emoji" }), "h"), null);
  assert.equal(images.teamsImageUrl(new FakeEl("img", { src: "https://example.com/a.png" }), "h"), null);
  assert.equal(images.teamsImageUrl(new FakeEl("img", { "data-orig-src": "https://evil.example/v1/objects/x" }), "h"), null);
});

test("loaded Teams images are saved from the tab copy and linked to the original", async () => {
  const blob1 = "blob:https://teams.cloud.microsoft/1";
  const img = new FakeEl("img", { src: blob1, "data-orig-src": ORIG, itemtype: "http://schema.skype.com/AMSImage", alt: "image" });
  const doc = makeContainer([img]);
  images.resolveTeamsImages(doc, []);
  const att = await images.collectAttachments(doc, [okFetch({ [blob1]: "JPEGDATA" })]);
  assert.deepEqual(att, [{ token: "qwc-attachment:0", mime: "image/jpeg", data: Buffer.from("JPEGDATA").toString("base64") }]);
  assert.equal(img.getAttribute("src"), "qwc-attachment:0");
  assert.equal(img.getAttribute("data-qwc-local"), null);
  assert.equal(img.parent.tagName, "A");
  assert.equal(img.parent.getAttribute("href"), ORIG);
});

test("each image gets its own token, and a repeat reuses it", async () => {
  const o2 = ORIG.replace(ID, "0-eau-d4-eaa8d28c7b4d396d50acd26724bec09c");
  const a = new FakeEl("img", { src: ORIG });
  const b = new FakeEl("img", { src: o2 });
  const c = new FakeEl("img", { src: ORIG });
  const doc = makeContainer([a, b, c]);
  const att = await images.collectAttachments(doc, okFetch({ [ORIG]: "A", [o2]: "B" }));
  assert.deepEqual(att.map((x) => x.token), ["qwc-attachment:0", "qwc-attachment:1"]);
  assert.deepEqual([a, b, c].map((i) => i.getAttribute("src")), ["qwc-attachment:0", "qwc-attachment:1", "qwc-attachment:0"]);
});

test("a failed download leaves no token: Teams keeps its online link, blob images are dropped", async () => {
  const teams = new FakeEl("img", { src: ORIG });
  const other = new FakeEl("img", { src: "blob:https://example.com/9" });
  const doc = makeContainer([teams, other]);
  const att = await images.collectAttachments(doc, okFetch({}));
  assert.deepEqual(att, []);
  assert.equal(teams.getAttribute("src"), ORIG);
  assert.equal(teams.parent.getAttribute("href"), ORIG);
  assert.equal(other.parent, null);
});

test("the next fetcher and source are tried when one fails", async () => {
  const blob1 = "blob:https://teams.cloud.microsoft/1";
  const img = new FakeEl("img", { src: ORIG, "data-qwc-local": blob1 });
  const doc = makeContainer([img]);
  const broken = async () => {
    throw new Error("Permission denied");
  };
  const att = await images.collectAttachments(doc, [broken, okFetch({ [ORIG]: "X" })]);
  assert.equal(att.length, 1);
  assert.equal(img.getAttribute("src"), "qwc-attachment:0");
});

test("Teams profile pictures are dropped, other images are kept", () => {
  const avatar = new FakeEl("img", {
    src: "https://teams.cloud.microsoft/api/mt/part/au-01/beta/users/u1/profilepicturev2/8:orgid:u2?size=HR64x64",
  });
  const photo = new FakeEl("img", { src: "https://example.com/a.png" });
  const doc = makeContainer([avatar, photo]);
  images.resolveTeamsImages(doc, []);
  assert.deepEqual(doc.querySelectorAll("img"), [photo]);
  assert.equal(images.isTeamsAvatar("https://teams.microsoft.com/api/mt/x/profilepicturev2/y"), true);
  assert.equal(images.isTeamsAvatar("https://example.com/profilepicture/1"), false);
});
