/* The Settings entries: the site, who the nodes publish as, and the script key a farm uses.
 *
 * One place, ComfyUI's own Settings dialog, under SG. Every entry is drawn by
 * this file rather than by ComfyUI's form controls, so nothing here enters ComfyUI's settings store,
 * which answers to anyone on the port: a value goes to the pack's own routes and lives in its
 * protected user directory. Each row saves on change, the way the rest of the dialog does. The
 * tooltips carry the full product name, so a search for "Flow" lands here as well.
 */
import { app } from "../../scripts/app.js";
import { styleOnce, esc } from "./fpt_dom_widgets.js";

// The sidebar entry. The full name truncates there, and SG is what the issue settled on for every
// short surface: the full product name or SG, nothing in between.
const CATEGORY = "SG";

const CSS = `
.fpt-set { display: flex; flex-direction: column; gap: 4px; width: 24rem; max-width: 100%; }
.fpt-set .fpt-line { display: flex; align-items: center; gap: 8px; }
.fpt-set input.p-inputtext, .fpt-set select.p-inputtext { width: 100% !important; flex: 1 1 auto; min-width: 0; }
.fpt-set .fpt-text { flex: 1 1 auto; min-width: 0; font-size: 13px; overflow-wrap: anywhere; }
.fpt-set .fpt-text.fpt-off { color: #e0b155; }
.fpt-set .fpt-text.fpt-bad { color: #e06c55; }
.fpt-set .fpt-note { font-size: 12px; opacity: .7; overflow-wrap: anywhere; }
.fpt-set button.p-button { white-space: nowrap; padding: 4px 10px; font-size: 13px; }
`;

const POLL_MS = 2000;               // the interval the site's own flow uses
const GIVE_UP_MS = 6 * 60 * 1000;   // the site forgets an unapproved request after about five minutes

/** One route, decoded. A failed request answers in a shape the rows can show. */
async function call(url, body) {
  try {
    const r = await fetch(url, body === undefined ? {} : {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    return await r.json();
  } catch (e) {
    return { error: `The ComfyUI server did not answer. ${e}` };
  }
}

// The last /fpt/session answer, shared by every row in the dialog, and the rows that draw it.
let status = null;
const rows = new Set();

function redraw() {
  for (const draw of [...rows]) {
    if (!draw.el.isConnected) rows.delete(draw);   // the dialog closed and took the row with it
    else draw();
  }
}

let loading = null;   // one request however many rows ask at once

function load() {
  loading = loading || call("/fpt/session").then((d) => { status = d; loading = null; redraw(); });
  return loading;
}

/** Tell every node on the canvas that who it publishes as has changed (probe 027: the site
 *  answers differently for a different caller). */
const announce = () => window.dispatchEvent(new CustomEvent("fpt:session"));

async function save(changes) {
  const d = await call("/fpt/settings", changes);
  if (!d.error) status = d;
  redraw();
  announce();
  return d;
}

/** Run `fn` on a node whenever the sign-in or the script key changes, for as long as the node
 *  lives. */
export function onSession(node, fn) {
  window.addEventListener("fpt:session", fn);
  const onRemoved = node.onRemoved;
  node.onRemoved = function () {
    window.removeEventListener("fpt:session", fn);
    return onRemoved?.apply(this, arguments);
  };
}

/** A row's root, with its draw function registered. `draw` runs now, from whatever is known, and
 *  again on every redraw. */
function row(draw) {
  styleOnce("fpt-settings", CSS);
  const el = document.createElement("div");
  el.className = "fpt-set";
  draw.el = el;
  rows.add(draw);
  draw();
  if (!status) load();
  return el;
}

function input(type, placeholder) {
  const i = document.createElement("input");
  i.type = type;
  i.className = "p-inputtext p-component";
  i.placeholder = placeholder;
  i.spellcheck = false;
  i.autocomplete = "off";
  return i;
}

function button(label) {
  const b = document.createElement("button");
  b.type = "button";
  b.className = "p-button p-component p-button-secondary p-button-sm";
  b.textContent = label;
  return b;
}

function line(...children) {
  const d = document.createElement("div");
  d.className = "fpt-line";
  d.append(...children);
  return d;
}

function text(cls = "") {
  const s = document.createElement("span");
  s.className = `fpt-text ${cls}`.trim();
  return s;
}

function note() {
  const s = document.createElement("div");
  s.className = "fpt-note";
  return s;
}

/** A text value that saves on change. The field is filled from the server's answer unless the
 *  operator is typing in it. */
function textRow(key, type, placeholder, fill = (s) => s[key] || "") {
  const i = input(type, placeholder);
  const n = note();
  i.addEventListener("change", async () => {
    const d = await save({ [key]: i.value.trim() });
    n.textContent = d.error || "";
  });
  const el = row(() => {
    if (document.activeElement !== i) i.value = fill(status || {});
  });
  el.append(i, n);
  return el;
}

const siteRow = () => textRow("site", "url", "https://yourstudio.shotgrid.autodesk.com");
const scriptNameRow = () => textRow("script_name", "text", "Script Name, from Admin > Scripts",
  (s) => (s.script_source === "environment" ? "" : s.script_name || ""));
const loginRow = () => textRow("login", "text", "Login on the People page, often an email");

/** The key is written and never read back, so the field only ever shows whether one is held. */
function keyRow() {
  const i = input("password", "");
  const n = note();
  i.addEventListener("change", async () => {
    if (!i.value) return;
    const d = await save({ api_key: i.value });
    i.value = "";
    n.textContent = d.error || "";
  });
  const clear = button("Clear");
  clear.addEventListener("click", async () => {
    const d = await save({ api_key: "", script_name: "" });
    n.textContent = d.error || "";
  });
  const el = row(() => {
    const s = status || {};
    if (s.script_source === "environment") {
      i.placeholder = "From environment";
    } else {
      i.placeholder = s.has_key ? "Saved. Paste another to replace" : "Application Key, from Admin > Scripts";
    }
    clear.hidden = !(s.has_key && s.script_source === "settings");
  });
  el.append(line(i, clear), n);
  return el;
}

/** Signed in, or the button that signs in: the App Session Launcher flow (probe 052). */
function signInRow() {
  const who = text();
  const btn = button("Sign in");
  const n = note();
  let polling = 0;

  const signIn = async () => {
    // Opened on the click, before any await, so the browser treats it as the operator's own tab
    // rather than a pop-up; the address is filled in once the site has issued it.
    const tab = window.open("", "_blank");
    const d = await call("/fpt/login", { site: (status && status.site) || "" });
    if (!d.url) {
      tab && tab.close();
      n.textContent = d.error || "The site did not issue a sign-in page. Check the site address, then try again.";
      return;
    }
    if (tab) tab.location = d.url; else window.open(d.url, "_blank");
    n.textContent = "Approve the sign-in in the tab that opened, then come back here.";
    const mine = ++polling;
    const started = Date.now();
    while (mine === polling && Date.now() - started < GIVE_UP_MS) {
      await new Promise((r) => setTimeout(r, POLL_MS));
      const p = await call(`/fpt/login?request_id=${encodeURIComponent(d.request_id)}`);
      if (p.state === "approved") {
        n.textContent = "";
        await load();
        announce();
        return;
      }
      if (p.state === "gone") {
        n.textContent = "That sign-in page has expired. Click Sign in again.";
        return;
      }
    }
    if (mine === polling) n.textContent = "Nobody approved the sign-in. Click Sign in to get a new page.";
  };

  const signOut = async () => {
    polling++;
    await call("/fpt/logout", {});
    n.textContent = "";
    await load();
    announce();
  };

  btn.addEventListener("click", () => (btn.textContent === "Sign out" ? signOut() : signIn()));

  const el = row(() => {
    const s = status || {};
    who.className = "fpt-text";
    if (s.how === "person" && s.alive) {
      who.textContent = `Signed in as ${s.who}. The nodes publish as you.`;
      btn.textContent = "Sign out";
    } else if (s.how === "person") {
      who.textContent = "Your sign-in has expired. Sign in again.";
      who.classList.add("fpt-off");
      btn.textContent = "Sign in";
    } else {
      who.textContent = "Not signed in. Approve one request in your browser and the nodes publish as you.";
      btn.textContent = "Sign in";
    }
    // The site is needed before a request can be made, so the button waits for it; the note goes
    // the moment the address arrives, and never overwrites a sign-in in progress.
    const waiting = !s.site && btn.textContent === "Sign in";
    btn.disabled = waiting;
    if (waiting) n.textContent = "Enter the site address first.";
    else if (n.textContent === "Enter the site address first.") n.textContent = "";
  });
  el.append(line(who, btn), n);
  return el;
}

/** What the nodes will publish as right now, and a button that proves it against the site. */
function connectionRow() {
  const who = text();
  const btn = button("Test");
  const n = note();
  btn.addEventListener("click", async () => {
    btn.disabled = true;
    n.textContent = "Asking the site…";
    const d = await call("/fpt/test", {});
    n.textContent = d.ok ? `Connected as ${d.who}.` : (d.error || "The site did not answer.");
    n.classList.toggle("fpt-bad", !d.ok);
    btn.disabled = false;
  });
  let shown = "";
  const el = row(() => {
    const s = status || {};
    // A test result describes one state of the settings; the next change makes it stale.
    const key = JSON.stringify([s.how, s.site, s.script_name, s.has_key, s.login]);
    if (key !== shown) { n.textContent = ""; n.classList.remove("fpt-bad"); shown = key; }
    who.className = "fpt-text";
    if (s.how === "person" && s.alive) {
      who.textContent = `Publishing as ${s.who}.`;
    } else if (s.how === "person") {
      who.textContent = "Your sign-in has expired. Sign in again below, or sign out to use the script key.";
      who.classList.add("fpt-off");
    } else if (s.how === "script") {
      who.textContent = `Publishing as script ${s.script_name}` +
        (s.login ? `, as ${s.login}.` : ".") +
        (s.script_source === "environment" ? " The key comes from the launch environment." : "");
    } else {
      who.textContent = "Not connected. Sign in, or enter a script name and application key.";
      who.classList.add("fpt-off");
    }
    btn.disabled = s.how === "none" || (s.how === "person" && !s.alive);
  });
  el.append(line(who, btn), n);
  return el;
}

// ---- Publish defaults: the profile, edited for the project the nodes open on ------------------

let defaults = null;      // the last /fpt/defaults answer
let loadingDefaults = null;

function loadDefaults() {
  loadingDefaults = loadingDefaults || call("/fpt/defaults").then((d) => {
    defaults = d; loadingDefaults = null; redraw();
  });
  return loadingDefaults;
}

async function saveDefault(key, value) {
  const d = await call("/fpt/defaults", { key, value });
  if (!d.error) defaults = d;
  redraw();
  announce();
  return d;
}

/** A row over the defaults rather than the session. */
function drow(draw) {
  const el = row(draw);
  if (!defaults) loadDefaults();
  return el;
}

const dval = (key) => (defaults && defaults.values && defaults.values[key]) ?? "";

/** A template with the example it produces, rendered by the node's own code on sample values. */
function templateRow(key, kind) {
  const i = input("text", "");
  const n = note();
  let typing;
  const example = async (t) => {
    const d = await call(`/fpt/preview_template?kind=${kind}&template=${encodeURIComponent(t)}`);
    n.textContent = d.error ? d.error : (d.example ? `Example: ${d.example}` : "");
  };
  i.addEventListener("input", () => { clearTimeout(typing); typing = setTimeout(() => example(i.value), 300); });
  i.addEventListener("change", async () => {
    const d = await saveDefault(key, i.value.trim());
    if (d.error) n.textContent = d.error; else example(i.value.trim());
  });
  let shown = null;
  const el = drow(() => {
    if (!defaults) return;
    i.placeholder = (defaults.placeholders || {})[key] || "";
    if (document.activeElement !== i) i.value = dval(key);
    if (shown !== dval(key)) { shown = dval(key); example(shown); }
  });
  el.append(i, n);
  return el;
}

function checkRow(key, label) {
  const i = document.createElement("input");
  i.type = "checkbox";
  i.style.cssText = "width:18px;height:18px;margin:0";
  const t = text();
  t.textContent = label;
  const n = note();
  i.addEventListener("change", async () => { const d = await saveDefault(key, i.checked); n.textContent = d.error || ""; });
  const el = drow(() => { i.checked = !!dval(key); });
  el.append(line(i, t), n);
  return el;
}

/** A native select, dressed as the dialog's own inputs. `options` is [{label, value}] and the
 *  first entry is the empty choice. */
function selectRow(key, options, onSave = saveDefault) {
  const sel = document.createElement("select");
  sel.className = "p-inputtext p-component";
  const n = note();
  sel.addEventListener("change", async () => { const d = await onSave(key, sel.value); n.textContent = d.error || ""; });
  const el = drow(() => {
    if (!defaults) return;
    const opts = options(defaults);
    sel.innerHTML = opts.map((o) => `<option value="${esc(o.value)}">${esc(o.label)}</option>`).join("");
    const cur = String(dval(key));
    sel.value = opts.some((o) => String(o.value) === cur) ? cur : String(opts[0]?.value ?? "");
  });
  el.append(sel, n);
  return el;
}

const projectRow = () => selectRow("default_project", (d) =>
  [{ label: "(none)", value: 0 }].concat((d.projects || []).map((p) => ({ label: p.label, value: p.id }))));
const storageRow = () => selectRow("published_files.storage", (d) =>
  [{ label: "(the only one, or pick one)", value: "" }].concat((d.storages || []).map((c) => ({ label: c, value: c }))));
const statusRow = () => selectRow("status", (d) =>
  [{ label: "(the site's default)", value: "" }].concat((d.statuses || []).map((s) => ({ label: s.label, value: s.code }))));
const colourRow = () => {
  const i = input("text", "sRGB");
  const n = note();
  i.addEventListener("change", async () => { const d = await saveDefault("published_files.colour_space", i.value.trim()); n.textContent = d.error || ""; });
  const el = drow(() => { if (document.activeElement !== i) i.value = dval("published_files.colour_space"); });
  el.append(i, n);
  return el;
};

// Every entry declares a value type ComfyUI never sees: `type` as a function draws the row, and
// the setter it is handed is never called, so the settings store keeps its default and nothing
// else. `defaultValue` is what addSetting insists on. The category path is three deep, the way
// ComfyUI's own are: the dialog keys its tree on the path, so two entries sharing one would show
// as one.
const entry = (id, name, group, type, tooltip) =>
  ({ id: `SG.${id}`, name, category: [CATEGORY, group, name], type, tooltip, defaultValue: "" });

// The dialog sorts groups by name and draws a group's rows in reverse registration order, so the
// group names are chosen to sort Connection, then the person, then the script, and the rows are
// listed last first.
const GROUP_SITE = "Connection";
const GROUP_DEFAULTS = "Defaults";
const GROUP_PERSON = "Publish as yourself";
const GROUP_SCRIPT = "Script key";

app.registerExtension({
  name: "comfyui-flow-production-tracking.settings",
  settings: [
    // Defaults, last row first. They edit the profile for the project the nodes open on; a graph
    // can still override the templates and the tick on the node itself.
    entry("ColourSpace", "Colour space", GROUP_DEFAULTS, colourRow,
      "The colour space new publishes declare, for example sRGB or ACEScg. Recorded with the "
      + "files, never applied to the pixels."),
    entry("ReviewMovie", "Review movie", GROUP_DEFAULTS, () => checkRow("published_files.register_movie",
      "Also keep the review movie under the storage"),
      "When a clip is published with its frames, copy the review movie beside them as a Published "
      + "File too."),
    entry("MoviePath", "Movie path", GROUP_DEFAULTS, () => templateRow("published_files.movie_path_template", "movie"),
      "Where a published clip lands under the storage. {version_name} is the Version's name and "
      + "{ext} the clip's own extension."),
    entry("SequencePath", "Sequence path", GROUP_DEFAULTS, () => templateRow("published_files.path_template", "sequence"),
      "Where a published image sequence lands under the storage, with %04d for the frame number."),
    entry("Storage", "Storage", GROUP_DEFAULTS, storageRow,
      "The Local File Storage the files are copied under, from Site Preferences > File Management "
      + "in Flow Production Tracking. A site with one needs no choice."),
    entry("PublishedFiles", "Published Files", GROUP_DEFAULTS, () => checkRow("published_files.default",
      "Create Published Files on a new Publish node"),
      "Whether a new Publish node registers the files beside the Version. The tick on the node "
      + "still decides per graph."),
    entry("Status", "Status", GROUP_DEFAULTS, statusRow,
      "The status a new Version gets. The site fills its own default when none is chosen."),
    entry("RootName", "Root name", GROUP_DEFAULTS, () => templateRow("root_name", "root"),
      "The Version name without its version number, for example sh010_roto. The file paths and "
      + "the Published File's Name are built on it."),
    entry("VersionName", "Version name", GROUP_DEFAULTS, () => templateRow("code_template", "name"),
      "How a new Version is named. {root_name} is the root name and {version:03d} the padded "
      + "number."),
    entry("Project", "Project", GROUP_DEFAULTS, projectRow,
      "The project the nodes open on. The defaults below are for it."),
    entry("PublishAs", "Publish as", GROUP_SCRIPT, loginRow,
      "The Login of the person the script publishes as, from the Login column on the People page. "
      + "Often their email address. Leave empty to publish as the script itself."),
    entry("ApplicationKey", "Application key", GROUP_SCRIPT, keyRow,
      "The Application Key shown once when the script was created. Kept on this ComfyUI, "
      + "never shown again."),
    entry("ScriptName", "Script name", GROUP_SCRIPT, scriptNameRow,
      "For a render farm or a machine nobody signs in on. The Script Name from the Scripts page "
      + "under Admin in Flow Production Tracking."),
    entry("SignIn", "Sign in", GROUP_PERSON, signInRow,
      "Approve one request in the browser where you are logged into Flow Production Tracking. "
      + "Every Version is then created by you. Wins over the script key while it lasts."),
    entry("Connection", "Publishing as", GROUP_SITE, connectionRow,
      "Who the nodes publish as right now. Test asks the site to confirm it."),
    entry("Site", "Site address", GROUP_SITE, siteRow,
      "Your Flow Production Tracking site. Example: https://yourstudio.shotgrid.autodesk.com"),
  ],
});
