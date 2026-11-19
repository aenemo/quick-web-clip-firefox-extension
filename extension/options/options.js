import "../compat.js";
import {
  moveDestination,
  normaliseSettings,
  removeDestination,
  setDefault,
  upsertDestination,
  validateDestination,
} from "../lib/settings.js";

const NATIVE_HOST = "quick_web_clip";
const HELPER_MISSING = "Helper not found. Run install.bat in the helper folder.";

const el = (id) => document.getElementById(id);
const body = el("dest-body");
const form = el("dest-form");

let settings = normaliseSettings(null);
let editingId = null;
let confirmingId = null;

async function load() {
  settings = normaliseSettings(await browser.storage.local.get(null));
  render();
}

async function save(next) {
  await browser.storage.local.set({
    destinations: next.destinations,
    datePosition: next.datePosition,
    timeFormat: next.timeFormat,
  });
  await load();
}

function make(tag, text, className) {
  const node = document.createElement(tag);
  if (text !== undefined) node.textContent = text;
  if (className) node.className = className;
  return node;
}

function button(text, onClick, disabled = false) {
  const b = make("button", text);
  b.type = "button";
  b.disabled = disabled;
  b.addEventListener("click", onClick);
  return b;
}

function renderRow(d, index, count) {
  const tr = document.createElement("tr");

  const radioCell = document.createElement("td");
  const radio = document.createElement("input");
  radio.type = "radio";
  radio.name = "default-destination";
  radio.checked = d.isDefault;
  radio.setAttribute("aria-label", `Make ${d.label} the default`);
  radio.addEventListener("change", () => save(setDefault(settings, d.id)));
  radioCell.append(radio);

  tr.append(radioCell, make("td", d.label), make("td", d.vaultPath, "path"), make("td", d.subfolder));

  const actions = make("td", undefined, "actions");
  if (confirmingId === d.id) {
    actions.append(
      make("span", `Delete ${d.label}?`, "confirm"),
      button("Yes", async () => {
        confirmingId = null;
        if (editingId === d.id) resetForm();
        await save(removeDestination(settings, d.id));
      }),
      button("No", () => {
        confirmingId = null;
        render();
      }),
    );
  } else {
    actions.append(
      button("Up", () => save(moveDestination(settings, d.id, -1)), index === 0),
      button("Down", () => save(moveDestination(settings, d.id, 1)), index === count - 1),
      button("Edit", () => startEdit(d)),
      button("Delete", () => {
        confirmingId = d.id;
        render();
      }),
    );
  }
  tr.append(actions);
  return tr;
}

function render() {
  body.replaceChildren(
    ...settings.destinations.map((d, i) => renderRow(d, i, settings.destinations.length)),
  );
  el("empty-note").hidden = settings.destinations.length > 0;
  el("date-position").value = settings.datePosition;
  el("time-format").value = settings.timeFormat;
}

function showErrors(errors) {
  el("e-label").textContent = errors.filter((e) => e.startsWith("Label")).join(". ");
  el("e-vault").textContent = errors.filter((e) => e.startsWith("Vault")).join(". ");
}

function resetForm() {
  editingId = null;
  form.reset();
  showErrors([]);
  el("form-title").textContent = "Add destination";
  el("f-submit").textContent = "Add";
  el("f-cancel").hidden = true;
}

function startEdit(d) {
  editingId = d.id;
  el("f-label").value = d.label;
  el("f-vault").value = d.vaultPath;
  el("f-sub").value = d.subfolder;
  showErrors([]);
  el("form-title").textContent = "Edit destination";
  el("f-submit").textContent = "Save";
  el("f-cancel").hidden = false;
  el("f-label").focus();
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  const existing = settings.destinations.find((d) => d.id === editingId);
  const candidate = {
    id: existing ? existing.id : crypto.randomUUID(),
    label: el("f-label").value.trim(),
    vaultPath: el("f-vault").value.trim(),
    subfolder: el("f-sub").value.trim(),
    // First destination becomes the default; edits keep their current default state.
    isDefault: existing ? existing.isDefault : settings.destinations.length === 0,
  };
  const errors = validateDestination(candidate);
  showErrors(errors);
  if (errors.length) return;
  resetForm();
  await save(upsertDestination(settings, candidate));
});

el("f-cancel").addEventListener("click", resetForm);

el("date-position").addEventListener("change", (event) => {
  save({ ...settings, datePosition: event.target.value });
});

el("time-format").addEventListener("change", (event) => {
  save({ ...settings, timeFormat: event.target.value });
});

async function checkHelper() {
  const status = el("helper-status");
  try {
    const reply = await browser.runtime.sendNativeMessage(NATIVE_HOST, { v: 1, action: "ping" });
    if (!reply || reply.ok !== true) throw new Error("bad reply");
    const yt = reply.ytDlp ? `yt-dlp ${reply.ytDlp}` : "yt-dlp not installed";
    status.textContent = `Helper connected (v${reply.version}), ${yt}`;
    status.className = "status ok";
  } catch (err) {
    status.textContent = HELPER_MISSING;
    status.className = "status bad";
  }
}

browser.storage.onChanged.addListener(load);

load();
checkHelper();
