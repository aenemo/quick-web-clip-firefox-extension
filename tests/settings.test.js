import test from "node:test";
import assert from "node:assert/strict";
import {
  DEFAULT_SETTINGS,
  normaliseSettings,
  validateDestination,
  getDefaultDestination,
  setDefault,
  removeDestination,
  upsertDestination,
  moveDestination,
  buildMenuModel,
} from "../extension/lib/settings.js";

const dest = (id, extra = {}) => ({
  id,
  label: "L" + id,
  vaultPath: "C:\\Vault" + id,
  subfolder: "",
  isDefault: false,
  ...extra,
});

const three = () => ({
  destinations: [dest("a", { isDefault: true }), dest("b"), dest("c")],
  datePosition: "end",
});

const ids = (s) => s.destinations.map((d) => d.id);
const defaults = (s) => s.destinations.map((d) => d.isDefault);

test("normaliseSettings of {} equals DEFAULT_SETTINGS", () => {
  assert.deepEqual(normaliseSettings({}), DEFAULT_SETTINGS);
  assert.deepEqual(normaliseSettings(undefined), DEFAULT_SETTINGS);
});

test("normaliseSettings makes the first destination default when none is", () => {
  const s = normaliseSettings({ destinations: [dest("a"), dest("b")] });
  assert.deepEqual(defaults(s), [true, false]);
});

test("normaliseSettings keeps only the first default", () => {
  const s = normaliseSettings({
    destinations: [dest("a", { isDefault: true }), dest("b", { isDefault: true })],
  });
  assert.deepEqual(defaults(s), [true, false]);
});

test("normaliseSettings rejects an unknown datePosition", () => {
  assert.equal(normaliseSettings({ datePosition: "middle" }).datePosition, "end");
  assert.equal(normaliseSettings({ datePosition: "start" }).datePosition, "start");
  assert.equal(normaliseSettings({ datePosition: "none" }).datePosition, "none");
});

test("normaliseSettings fills a missing subfolder", () => {
  const s = normaliseSettings({ destinations: [{ id: "a", label: "A", vaultPath: "C:\\V" }] });
  assert.equal(s.destinations[0].subfolder, "");
});

test("validateDestination accepts a valid destination", () => {
  assert.deepEqual(validateDestination(dest("a")), []);
});

test("validateDestination requires label and vault folder", () => {
  assert.deepEqual(validateDestination({ label: " ", vaultPath: "" }), [
    "Label is required",
    "Vault folder is required",
  ]);
});

test("validateDestination accepts a drive path", () => {
  assert.deepEqual(validateDestination({ label: "x", vaultPath: "C:\\Vault" }), []);
});

test("validateDestination accepts a UNC path", () => {
  assert.deepEqual(validateDestination({ label: "x", vaultPath: "\\\\server\\share" }), []);
});

test("validateDestination rejects a relative path", () => {
  assert.deepEqual(validateDestination({ label: "x", vaultPath: "Vault" }), [
    "Vault folder must be a full path",
  ]);
});

test("getDefaultDestination returns the default or null", () => {
  assert.equal(getDefaultDestination(three()).id, "a");
  assert.equal(getDefaultDestination(DEFAULT_SETTINGS), null);
});

test("setDefault moves the default and does not mutate", () => {
  const s = three();
  const out = setDefault(s, "c");
  assert.deepEqual(defaults(out), [false, false, true]);
  assert.equal(s.destinations[0].isDefault, true);
  assert.notEqual(out, s);
});

test("removeDestination reassigns default", () => {
  const out = removeDestination(three(), "a");
  assert.deepEqual(ids(out), ["b", "c"]);
  assert.equal(getDefaultDestination(out).id, "b");
});

test("removeDestination of a non-default keeps the default", () => {
  const out = removeDestination(three(), "b");
  assert.equal(getDefaultDestination(out).id, "a");
});

test("removeDestination of the last destination leaves none", () => {
  const only = { destinations: [dest("a", { isDefault: true })], datePosition: "end" };
  const out = removeDestination(only, "a");
  assert.deepEqual(out.destinations, []);
  assert.equal(getDefaultDestination(out), null);
});

test("upsertDestination adds and replaces without mutating", () => {
  const s = three();
  assert.deepEqual(ids(upsertDestination(s, dest("d"))), ["a", "b", "c", "d"]);
  const replaced = upsertDestination(s, dest("b", { label: "New" }));
  assert.equal(replaced.destinations[1].label, "New");
  assert.equal(replaced.destinations.length, 3);
  assert.equal(s.destinations[1].label, "Lb");
});

test("upsertDestination of the first destination makes it default", () => {
  const out = upsertDestination(DEFAULT_SETTINGS, dest("a"));
  assert.equal(getDefaultDestination(out).id, "a");
});

test("upsertDestination with isDefault moves the default", () => {
  const out = upsertDestination(three(), dest("c", { isDefault: true }));
  assert.deepEqual(defaults(out), [false, false, true]);
});

test("moveDestination reorders and clamps", () => {
  assert.deepEqual(ids(moveDestination(three(), "c", -1)), ["a", "c", "b"]);
  assert.deepEqual(ids(moveDestination(three(), "a", 1)), ["b", "a", "c"]);
  assert.deepEqual(ids(moveDestination(three(), "a", -1)), ["a", "b", "c"]);
  assert.deepEqual(ids(moveDestination(three(), "c", 1)), ["a", "b", "c"]);
});

test("buildMenuModel marks exactly one default", () => {
  const m = buildMenuModel(three());
  assert.deepEqual(m.map((x) => x.id), ["dest:a", "dest:b", "dest:c"]);
  assert.deepEqual(m.map((x) => x.title), ["La (default)", "Lb", "Lc"]);
  assert.equal(m.filter((x) => x.title.includes(" (default)")).length, 1);
});

test("setDefault with an unknown id keeps the existing default", () => {
  const out = setDefault(three(), "zz");
  assert.deepEqual(defaults(out), [true, false, false]);
});

test("normaliseSettings drops malformed destination entries", () => {
  const s = normaliseSettings({ destinations: [null, "x", 5, { label: "no id" }, dest("a")] });
  assert.deepEqual(ids(s), ["a"]);
  assert.deepEqual(defaults(s), [true]);
});

test("normaliseSettings treats a non-array destinations as empty", () => {
  assert.deepEqual(normaliseSettings({ destinations: "nope" }).destinations, []);
  assert.deepEqual(normaliseSettings({ destinations: {} }).destinations, []);
});

test("normaliseSettings keeps a known timeFormat and defaults to 12-hour", () => {
  assert.equal(normaliseSettings({}).timeFormat, "12h");
  assert.equal(normaliseSettings({ timeFormat: "24h" }).timeFormat, "24h");
  assert.equal(normaliseSettings({ timeFormat: "13h" }).timeFormat, "12h");
});
