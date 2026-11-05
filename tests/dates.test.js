process.env.TZ = "Australia/Sydney";

import test from "node:test";
import assert from "node:assert/strict";
import { localDate, normalisePublished } from "../extension/lib/dates.js";

test("localDate uses local time", () => {
  assert.equal(localDate(new Date(2026, 10, 5, 23, 59)), "2026-11-05");
});

test("localDate pads month and day", () => {
  assert.equal(localDate(new Date(2026, 0, 3, 0, 1)), "2026-01-03");
});

test("normalisePublished converts ISO date-time to local date", () => {
  assert.equal(normalisePublished("2026-03-14T08:00:00+10:00"), "2026-03-14");
});

test("normalisePublished keeps plain dates unchanged", () => {
  assert.equal(normalisePublished("2026-03-14"), "2026-03-14");
});

test("normalisePublished handles other Date.parse formats", () => {
  assert.equal(normalisePublished("March 14, 2026 10:00:00"), "2026-03-14");
});

test("normalisePublished returns null for garbage and empty input", () => {
  assert.equal(normalisePublished("garbage"), null);
  assert.equal(normalisePublished(null), null);
  assert.equal(normalisePublished(""), null);
});
