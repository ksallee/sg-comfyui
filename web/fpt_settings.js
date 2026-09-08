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
.fpt-switch { position: relative; flex: none; width: 40px; height: 22px; border-radius: 11px;
              background: var(--p-toggleswitch-background, #4a4e55); transition: background .15s; }
.fpt-switch.on { background: var(--p-toggleswitch-checked-background, #2b7fd6); }
.fpt-switch i { position: absolute; top: 3px; left: 3px; width: 16px; height: 16px; border-radius: 50%;
                background: var(--p-toggleswitch-handle-background, #fff); transition: left .15s; }
.fpt-switch.on i { left: 21px; }
.fpt-switch input { position: absolute; inset: 0; width: 100%; height: 100%; margin: 0; opacity: 0; cursor: pointer; }
`;

const POLL_MS = 2000;               // the interval the site's own flow uses
const GIVE_UP_MS = 6 * 60 * 1000;   // the site forgets an unapproved request after about five minutes

/** One route, decoded. A failed request answers in a shape the rows can show. */
async function call(url, body) {
  let r;
  try {
    r = await fetch(url, body === undefined ? {} : {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
  } catch (e) {
    return { error: `The ComfyUI server did not answer. ${e}` };
  }
  // Routes register when ComfyUI imports the pack, so a 404 is a server older than this page.
  if (r.status === 404) return { error: RESTART };
  try {
    return await r.json();
  } catch (e) {
    return { error: `The ComfyUI server answered ${r.status} instead of JSON. ${RESTART}` };
  }
}

const RESTART = "Restart ComfyUI, then reload this page: the running server predates this version of the pack.";

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

/** Where the script comes from, in one line under its rows. */
const scriptSource = (s) => !status ? "" : s.script_source === "environment" ? "From the environment."
  : s.script_source === "settings" ? "Saved on this ComfyUI." : "Not set.";

function scriptNameRow() {
  const i = input("text", "Script Name, from Admin > Scripts");
  const n = note();
  i.addEventListener("change", async () => {
    const d = await save({ script_name: i.value.trim() });
    if (d.error) n.textContent = d.error;
  });
  const el = row(() => {
    const s = status || {};
    if (document.activeElement !== i) i.value = s.typed_script_name || s.script_name || "";
    n.textContent = (s.typed_script_name && s.script_source !== "settings")
      ? "Paste its Application Key below to use it." : scriptSource(s);
  });
  el.append(i, n);
  return el;
}

function loginRow() {
  const i = input("text", "Login on the People page, often an email");
  const n = note();
  i.addEventListener("change", async () => {
    const d = await save({ login: i.value.trim() });
    if (d.error) n.textContent = d.error;
  });
  const el = row(() => {
    const s = status || {};
    if (document.activeElement !== i) i.value = s.login || "";
    n.textContent = !status ? "" : s.login ? `The script publishes as ${s.login}.` : "Not set. The script publishes as itself.";
  });
  el.append(i, n);
  return el;
}

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
    i.placeholder = s.has_key ? "Paste a key to replace it" : "Application Key, from Admin > Scripts";
    n.textContent = !status ? "" : s.script_source === "environment" ? "Set, from the environment. A key pasted here is used instead."
      : s.script_source === "settings" ? "Saved on this ComfyUI. Never shown."
      : "Not set. Shown once, when the script is made under Admin > Scripts.";
    clear.hidden = !(s.has_key && s.script_source === "settings");
  });
  el.append(line(i, clear), n);
  return el;
}

/** Signed in, or the button that signs in: the App Session Launcher flow (probe 052). */
function signInRow() {
  const who = text();
  const btn = button("Log in");
  const n = note();
  let polling = 0;

  const signIn = async () => {
    // Opened on the click, before any await, so the browser treats it as the operator's own tab
    // rather than a pop-up; the address is filled in once the site has issued it.
    const tab = window.open("", "_blank");
    const d = await call("/fpt/login", { site: (status && status.site) || "" });
    if (!d.url) {
      tab && tab.close();
      n.textContent = d.error || "The site did not issue a login page. Check the site address, then try again.";
      return;
    }
    if (tab) tab.location = d.url; else window.open(d.url, "_blank");
    n.textContent = "Approve the login in the tab that opened, then come back here.";
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
        n.textContent = "That login page has expired. Click Log in again.";
        return;
      }
    }
    if (mine === polling) n.textContent = "Nobody approved the login. Click Log in to get a new page.";
  };

  const signOut = async () => {
    polling++;
    await call("/fpt/logout", {});
    n.textContent = "";
    await load();
    announce();
  };

  btn.addEventListener("click", () => (btn.textContent === "Log out" ? signOut() : signIn()));

  const el = row(() => {
    const s = status || {};
    who.className = "fpt-text";
    if (!status) {
      who.textContent = "Checking…";
      btn.disabled = true;
      return;
    }
    if (s.how === "person" && s.alive) {
      who.textContent = `Logged in as ${s.who}. The nodes publish as you.`;
      btn.textContent = "Log out";
    } else if (s.how === "person") {
      who.textContent = "Your login has expired. Log in again.";
      who.classList.add("fpt-off");
      btn.textContent = "Log in";
    } else {
      who.textContent = "Not logged in. Approve one request in your browser and the nodes publish as you.";
      btn.textContent = "Log in";
    }
    // The site is needed before a request can be made, so the button waits for it; the note goes
    // the moment the address arrives, and never overwrites a sign-in in progress.
    const waiting = !s.site && btn.textContent === "Log in";
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
    if (!status) {
      who.textContent = "Checking…";
      btn.disabled = true;
      return;
    }
    if (s.error) n.textContent = s.error;   // a route that failed, an old server most often
    if (s.how === "person" && s.alive) {
      who.textContent = `Publishing as ${s.who}.`;
    } else if (s.how === "person") {
      who.textContent = "Your login has expired. Log in again below, or log out to use the script.";
      who.classList.add("fpt-off");
    } else if (s.how === "script") {
      who.textContent = `Publishing as script ${s.script_name}` +
        (s.login ? `, as ${s.login}.` : ".") +
        (s.script_source === "environment" ? " The key comes from the launch environment." : "");
    } else {
      who.textContent = "Not connected. Log in, or enter a script name and application key.";
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
    const isDefault = !dval(key) || t === (defaults.placeholders || {})[key];
    // A path is long enough on its own: the two path rows show the bare result.
    const bare = kind === "sequence" || kind === "movie";
    n.textContent = d.error ? d.error : !d.example ? ""
      : bare ? d.example : `Example: ${d.example}${isDefault ? " (the default)" : ""}`;
  };
  i.addEventListener("input", () => { clearTimeout(typing); typing = setTimeout(() => example(i.value), 300); });
  i.addEventListener("change", async () => {
    // Typing the default back in is the same as clearing it, so the profile carries no copy of it.
    const v = i.value.trim();
    const d = await saveDefault(key, v === (defaults.placeholders || {})[key] ? "" : v);
    if (d.error) n.textContent = d.error; else example(v || (defaults.placeholders || {})[key]);
  });
  let shown = null;
  const el = drow(() => {
    if (!defaults) { i.placeholder = "Loading…"; return; }
    const fallback = (defaults.placeholders || {})[key] || "";
    const inForce = dval(key) || fallback;
    if (document.activeElement !== i) i.value = inForce;
    if (shown !== inForce) { shown = inForce; example(inForce); }
  });
  el.append(i, n);
  return el;
}

/** A boolean, drawn as a switch like the dialog's own. The frontend's switch is a Vue component
 *  with no reusable markup, so this is the same shape in the same colours. */
function toggleRow(key) {
  const box = document.createElement("label");
  box.className = "fpt-switch";
  box.innerHTML = '<input type="checkbox" role="switch"><i></i>';
  const i = box.querySelector("input");
  const n = note();
  const paint = () => box.classList.toggle("on", i.checked);
  i.addEventListener("change", async () => {
    paint();
    const d = await saveDefault(key, i.checked);
    n.textContent = d.error || "";
  });
  const el = drow(() => { i.checked = !!dval(key); paint(); });
  el.append(line(box), n);
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
    if (!defaults) { sel.innerHTML = "<option>Loading…</option>"; return; }
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
const storageRow = () => selectRow("published_files.storage", (d) => {
  const found = (d.storages || []).map((s) => ({ label: s.code, value: s.code }));
  if (found.length === 1) return found;          // the only root there is: shown, not asked
  if (!found.length) return [{ label: "(no Local File Storage on the site)", value: "" }];
  return [{ label: "(pick one)", value: "" }].concat(found);
});
/** The storage row the picker names, or the only one. */
const pickedStorage = (d) => {
  const code = String(dval("published_files.storage"));
  const rows = d.storages || [];
  return rows.find((s) => s.code === code) || (rows.length === 1 ? rows[0] : null);
};

const PLATFORM = { mac: "Mac", linux: "Linux", windows: "Windows" };

/** The platforms the picked storage defines a root for, first the machine's own, so the unset
 *  value shows what the publish will do. */
const platformRow = () => selectRow("published_files.path_platform", (d) => {
  const row = pickedStorage(d) || {};
  const have = Object.keys(PLATFORM).filter((p) => row[p]);
  if (!have.length) return [{ label: "(the storage defines no path)", value: "" }];
  const mine = have.includes(d.this_platform) ? d.this_platform : have[0];
  return have.map((p) => ({ label: `${PLATFORM[p]} (${row[p]})`, value: p }))
    .sort((a, b) => (a.value === mine ? -1 : b.value === mine ? 1 : 0));
});

const statusRow = () => selectRow("status", (d) =>
  [{ label: "(the site's default)", value: "" }].concat((d.statuses || []).map((s) => ({ label: `${s.label} (${s.code})`, value: s.code }))));
const colourRow = () => {
  const i = input("text", "sRGB");
  const n = note();
  i.addEventListener("change", async () => { const d = await saveDefault("published_files.colour_space", i.value.trim()); n.textContent = d.error || ""; });
  const el = drow(() => {
    i.placeholder = defaults ? "sRGB" : "Loading…";
    if (document.activeElement !== i) i.value = dval("published_files.colour_space");
  });
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

// The dialog draws a group's rows in reverse registration order, so the rows are listed last first.
// Group names sort alphabetically in the dialog, and these are chosen to read top to bottom as
// Connection, Log In, Script Authentication, then the defaults.
const GROUP_SITE = "Connection";
const GROUP_PERSON = "Log In As Yourself";
const GROUP_SCRIPT = "Script Authentication";
const GROUP_DEFAULTS = "SG Defaults";
const GROUP_PUBLISH = "SG Publish Defaults";

app.registerExtension({
  name: "comfyui-flow-production-tracking.settings",
  settings: [
    // Defaults, last row first. They edit the profile for the project the nodes open on; a graph
    // can still override the templates and the tick on the node itself.
    entry("ColourSpace", "Colour space", GROUP_PUBLISH, colourRow,
      "The colour space new publishes declare, for example sRGB or ACEScg. Recorded with the "
      + "files, never applied to the pixels."),
    entry("PathToMovie", "Path to Movie", GROUP_PUBLISH, () => toggleRow("published_files.path_to_movie"),
      "Fill the Version's Path to Movie field with the published clip's path, written for the "
      + "operating system chosen above."),
    entry("PathToFrames", "Path to Frames", GROUP_PUBLISH, () => toggleRow("published_files.path_to_frames"),
      "Fill the Version's Path to Frames field with the frame pattern, written for the operating "
      + "system chosen above, so people on that system open the frames in place."),
    entry("ReviewMovie", "Review movie", GROUP_PUBLISH, () => toggleRow("published_files.register_movie"),
      "When a clip is published with its frames, also copy the review movie beside them as a "
      + "Published File."),
    entry("MoviePath", "Movie path", GROUP_PUBLISH, () => templateRow("published_files.movie_path_template", "movie"),
      "Where a published clip lands, relative to the storage root. {version_name} is the "
      + "Version's name and {ext} the clip's own extension."),
    entry("SequencePath", "Sequence path", GROUP_PUBLISH, () => templateRow("published_files.path_template", "sequence"),
      "Where a published image sequence lands, relative to the storage root, with %04d for the "
      + "frame number."),
    entry("Platform", "Operating system", GROUP_PUBLISH, platformRow,
      "Which of the storage's roots the Version's Path to Frames and Path to Movie are written with. "
      + "A path field holds one absolute path, so it reads on one system. First is this machine's."),
    entry("Storage", "Storage", GROUP_PUBLISH, storageRow,
      "The Local File Storage the files are copied under, from Site Preferences > File Management "
      + "in Flow Production Tracking."),
    entry("CreatePublishedFiles", "Create Published Files", GROUP_PUBLISH, () => toggleRow("published_files.default"),
      "Whether a new Publish node registers the files beside the Version. The tick on the node "
      + "still decides per graph, and the rows below apply whenever it is ticked."),
    entry("Status", "Status", GROUP_PUBLISH, statusRow,
      "The status a new Version gets. The site fills its own default when none is chosen."),
    entry("VersionName", "Version name", GROUP_PUBLISH, () => templateRow("code_template", "name"),
      "How a new Version is named. {root_name} is the root name and {version:03d} the padded "
      + "number. Any Version field works as a token, dotted paths included, and an empty one "
      + "drops out."),
    entry("RootName", "Root name", GROUP_PUBLISH, () => templateRow("root_name", "root"),
      "The Version name without its version number, for example sh010_RTO. The file paths and "
      + "the Published File's Name are built on it. A token with no value drops out with its "
      + "separator, so a Version with no Task keeps the entity alone."),
    entry("Project", "Project", GROUP_DEFAULTS, projectRow,
      "The project both nodes open on. The publish defaults below are for it."),
    entry("PublishAs", "Publish as", GROUP_SCRIPT, loginRow,
      "The Login of the person the script publishes as, from the Login column on the People page. "
      + "Often their email address. Leave empty to publish as the script itself."),
    entry("ApplicationKey", "Application key", GROUP_SCRIPT, keyRow,
      "The Application Key shown once when the script was created. Kept on this ComfyUI, "
      + "never shown again."),
    entry("ScriptName", "Script name", GROUP_SCRIPT, scriptNameRow,
      "For a render farm or a machine nobody signs in on. The Script Name from the Scripts page "
      + "under Admin in Flow Production Tracking."),
    entry("LogIn", "Log in", GROUP_PERSON, signInRow,
      "Approve one request in the browser where you are logged into Flow Production Tracking. "
      + "Every Version is then created by you. Wins over the script key while it lasts."),
    entry("Connection", "Publishing as", GROUP_SITE, connectionRow,
      "Who the nodes publish as right now. Test asks the site to confirm it."),
    entry("Site", "Site address", GROUP_SITE, siteRow,
      "Your Flow Production Tracking site. Example: https://yourstudio.shotgrid.autodesk.com"),
  ],
});
