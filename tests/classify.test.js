import test from "node:test";
import assert from "node:assert/strict";
import { classifyUrl, isClippable } from "../extension/lib/classify.js";

const VIDEO_URLS = [
  "https://www.youtube.com/watch?v=abc123",
  "https://www.youtube.com/shorts/abc123",
  "https://www.youtube.com/live/abc123",
  "https://youtu.be/abc123",
  "https://m.youtube.com/watch?v=abc123",
  "https://vimeo.com/123456789",
  "https://www.dailymotion.com/video/x8abc",
  "https://www.ted.com/talks/some_speaker_some_title",
];

for (const url of VIDEO_URLS) {
  test(`classifyUrl: video for ${url}`, () => {
    assert.equal(classifyUrl(url), "video");
  });
}

test("classifyUrl: site roots and non-video pages are articles", () => {
  assert.equal(classifyUrl("https://www.youtube.com/"), "article");
  assert.equal(classifyUrl("https://vimeo.com/about"), "article");
  assert.equal(classifyUrl("https://example.com/post"), "article");
});

test("classifyUrl: og:type video overrides the URL", () => {
  assert.equal(classifyUrl("https://example.com/post", "video.other"), "video");
  assert.equal(classifyUrl("https://example.com/post", "article"), "article");
  assert.equal(classifyUrl("https://example.com/post", null), "article");
});

test("classifyUrl: unparseable URL is an article", () => {
  assert.equal(classifyUrl("not a url"), "article");
});

test("isClippable rejects non-web schemes", () => {
  assert.equal(isClippable("about:blank"), false);
  assert.equal(isClippable("moz-extension://abc/page.html"), false);
  assert.equal(isClippable("view-source:https://example.com"), false);
  assert.equal(isClippable("not a url"), false);
});

test("isClippable rejects addons.mozilla.org and PDFs", () => {
  assert.equal(isClippable("https://addons.mozilla.org/en-US/firefox/"), false);
  assert.equal(isClippable("https://x.com/a.pdf"), false);
  assert.equal(isClippable("https://x.com/a.PDF"), false);
  assert.equal(isClippable("file:///C:/docs/a.pdf"), false);
});

test("isClippable accepts http, https and file", () => {
  assert.equal(isClippable("https://example.com"), true);
  assert.equal(isClippable("http://example.com/a.pdf.html"), true);
  assert.equal(isClippable("file:///C:/docs/a.html"), true);
});

test("classifyUrl: vimeo path must be a whole numeric id", () => {
  assert.equal(classifyUrl("https://vimeo.com/123abc"), "article");
  assert.equal(classifyUrl("https://vimeo.com/123/abc"), "video");
  assert.equal(classifyUrl("https://vimeo.com/video/123"), "video");
});
