import { test } from "node:test";
import assert from "node:assert/strict";

// teams.js is a classic content script: loading it defines globalThis.__qwcTeams.
await import("../extension/content/teams.js");
const teams = globalThis.__qwcTeams;

const timeEl = (text, datetime) => ({
  textContent: text,
  getAttribute: (name) => (name === "datetime" ? datetime : null),
});

test("only Teams hosts get the chat clean-up", () => {
  for (const h of ["teams.cloud.microsoft", "teams.microsoft.com", "teams.live.com"]) assert.equal(teams.isTeamsHost(h), true, h);
  for (const h of ["example.com", "notteams.microsoft.com.evil.net", "microsoft.com"]) assert.equal(teams.isTeamsHost(h), false, h);
});

test("message times show the date in Australian order", () => {
  assert.match(teams.messageTime(timeEl("9:13 AM", "2026-11-18T23:13:00.000Z")), /^\d{2}\/\d{2}\/2026 \d{1,2}:\d{2}\s?[ap]m$/i);
});

test("a message time without a usable datetime stays as shown", () => {
  assert.equal(teams.messageTime(timeEl(" 9:13 AM ", "")), "9:13 AM");
  assert.equal(teams.messageTime(timeEl("Yesterday", "not a date")), "Yesterday");
});
