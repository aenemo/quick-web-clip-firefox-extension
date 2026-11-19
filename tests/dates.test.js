process.env.TZ = "Australia/Sydney";

import test from "node:test";
import assert from "node:assert/strict";
import { localDate, localTime, normalisePublished } from "../extension/lib/dates.js";

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

test("normalisePublished rejects an impossible calendar date", () => {
  assert.equal(normalisePublished("2026-02-30"), null);
});

test("normalisePublished converts a UTC time to the next local day", () => {
  assert.equal(normalisePublished("2026-03-14T23:30:00Z"), "2026-03-15");
});

test("localTime gives 12-hour time by default and 24-hour on request", () => {
  const at = (h, m) => new Date(2026, 10, 19, h, m);
  assert.equal(localTime(at(14, 5)), "2:05 pm");
  assert.equal(localTime(at(0, 7), "12h"), "12:07 am");
  assert.equal(localTime(at(12, 0), "12h"), "12:00 pm");
  assert.equal(localTime(at(9, 30), "12h"), "9:30 am");
  assert.equal(localTime(at(14, 5), "24h"), "14:05");
  assert.equal(localTime(at(0, 7), "24h"), "00:07");
});
