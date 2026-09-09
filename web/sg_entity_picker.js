/* The editor half of both nodes: the site-backed pickers, the readout, and the round trips that
 * feed them.
 *
 * Every picker searches the SITE, never the page the site already sent — a browser-side substring
 * over what is loaded finds `giraffe_ruler` for `f` and not for `f r`, which is what made a bespoke
 * box worse than none.
 */
import { app } from "../../scripts/app.js";
import { addPanel } from "./sg_panel.js";
import { onSession } from "./sg_settings.js";
import { searchPicker, chipSelect, hideWidget, requireVueNodes, fitNode, dontSerialize,
         restoreDeclaredWidgets, restoreValue, textRows, cascade, call } from "./sg_dom_widgets.js";

const NONE = "(none)";        // a visible "no value"; an empty option cannot be clicked

/** The site's own value for a label. "(none)" is a label for the operator. */
const bare = (v) => (!v || v === NONE) ? "" : v;

/** The type out of a `name (Type)` label — context on the row, never part of what is searched. */
// Which of a node definition's inputs are widgets, in declared order. An input slot carries a type
// name this list does not hold, so it is skipped; a combo arrives as an array of its labels.
// Allowed types are named rather than excluded, because a new slot type would otherwise be counted
// as a widget and shift every value after it.
const WIDGET_TYPES = new Set(["STRING", "INT", "FLOAT", "BOOLEAN", "COMBO"]);

function declaredWidgets(nodeData) {
  const out = [];
  for (const section of ["required", "optional"]) {
    for (const [name, spec] of Object.entries(nodeData?.input?.[section] || {})) {
      if (Array.isArray(spec?.[0]) || WIDGET_TYPES.has(spec?.[0])) out.push(name);
    }
  }
  return out;
}

function typeFromLabel(label) {
  const m = /\s\(([^()]+)\)$/.exec(label || "");
  return m ? m[1] : "";
}

/** The same label without its trailing type. */
const withoutType = (label) => String(label ?? "").replace(/\s\([^()]+\)$/, "");

/** Keep a combo's options in step with the site without touching its value unless the value is
 *  gone, and answer the site's sentence if it sent one.
 *
 *  An answer carrying `error` leaves both the options and the value alone: a login that expired
 *  while the graph was opening would otherwise reset link, task and status to "(none)" and the next
 *  Run would publish an unlinked Version. */
function setOptions(widget, d, keep) {
  if (!widget) return "";
  if (d.error) return d.error;
  widget.options.values = [NONE].concat((d.items || []).map((x) => x.label));
  const wanted = keep ?? widget.value;
  widget.value = widget.options.values.includes(wanted) ? wanted : widget.options.values[0];
  return "";
}

/** Chain `after` onto a widget's callback, keeping whatever was already there. */
function wrap(widget, after) {
  if (!widget) return;
  const prev = widget.callback;
  widget.callback = function (value) {
    const r = prev?.apply(this, arguments);
    after(value);
    return r;
  };
}

/** A project as a picker row: a show is recognised by its thumbnail and code as much as by its
 *  name. `image` is a presigned URL re-signed on every read (field_types/image). */
const projectCard = (x) => ({ name: x.label, code: x.code || "", image: x.image || "",
                              value: x.label });

/** The project picker both nodes carry. A studio site has hundreds of projects, so this searches
 *  name and code instead of asking anyone to scroll a combo. */
function projectPicker(node, widget, state, onPick) {
  hideWidget(widget);
  return searchPicker(node, widget, {
    label: "project",
    placeholder: "search projects",
    empty: "No project matches those words.",
    search: async (q, { live, signal }) => {
      const d = await call("/sg/projects", { signal });
      if (!live()) return [];      // a superseded search records nothing
      state.projects = d.items || [];
      const terms = q.toLowerCase().split(/\s+/).filter(Boolean);
      const hay = (x) => `${x.label} ${x.code || ""}`.toLowerCase();
      return state.projects.filter((x) => terms.every((t) => hay(x).includes(t))).map(projectCard);
    },
    onPick,
  });
}

/** Read the projects, point `state` at the one picked, and keep the hidden combo legal. Answers the
 *  sentence to show, or "".
 *
 * The picked value is read AFTER the fetch: ComfyUI applies a saved graph's widget values while
 * this is in flight, so a value captured before the await is stale and writing it back reverts the
 * node to the default project.
 */
async function selectProject(widget, state, picked, tok) {
  const d = await call("/sg/projects", tok);
  if (!tok.live) return "";
  if (d.error) return d.error;
  state.projects = d.items || [];
  let chosen = picked ?? widget.value;
  // "(none)" in a saved graph is no choice, and no choice means the project under Settings, the
  // same one a fresh node opens on. A template therefore lands on the operator's show.
  if (!bare(chosen)) chosen = (state.projects.find((x) => x.id === d.default) || {}).label || chosen;
  const row = state.projects.find((x) => x.label === chosen);
  state.projectId = row?.id || 0;
  widget.options.values = [NONE].concat(state.projects.map((x) => x.label));
  // A project this login cannot see stays on the widget rather than being replaced by "(none)":
  // the graph names a real show, and an operator who signs in as themselves gets it back.
  restoreValue(widget, chosen || NONE);
  return (row || !bare(chosen))
    ? "" : `No project named ${chosen} on this site. Pick one from the list.`;
}

/** The row behind the combo's current value, so the trigger carries the project's thumbnail. */
function currentProject(widget, state) {
  const row = state.projects.find((x) => x.label === widget.value);
  return row && projectCard(row);
}

/** The link picker both nodes carry. `contains` runs on the site (probe 017), so two words find one
 *  entity out of thousands and each row carries the type it will be linked as. Every row seen
 *  records its id in `state.linkIds`, which is what turns a picked label back into an entity id. */
function linkPicker(node, widget, state, { empty, onPick }) {
  hideWidget(widget);
  return searchPicker(node, widget, {
    label: "link",
    placeholder: "search links",
    empty,
    search: async (q, { live, signal }) => {
      const d = await call(`/sg/entities?project_id=${state.projectId}` +
        `&q=${encodeURIComponent(q)}`, { signal });
      if (!live()) return [];      // a superseded search records no ids
      for (const x of d.items || []) state.linkIds[x.label] = x.id;
      return (d.items || []).map((x) => ({
        name: withoutType(x.label), type: x.type, value: x.label,
      }));
    },
    onPick,
  });
}

/** Every link on the project, into the hidden combo. Hidden, it still holds the value, so its
 *  options must stay legal for a saved graph whose link this project does not have. */
async function loadLinkOptions(widget, state, tok) {
  const d = await call(`/sg/entities?project_id=${state.projectId}`, tok);
  if (!tok.live) return "";
  if (d.error) return d.error;
  state.linkIds = Object.fromEntries((d.items || []).map((x) => [x.label, x.id]));
  return setOptions(widget, d);
}

/** The tasks on one link, into the `task` combo. */
async function loadTaskOptions(widget, type, id, tok) {
  const d = await call(`/sg/tasks?type=${encodeURIComponent(type)}&id=${id || 0}`, tok);
  if (!tok.live) return "";
  return setOptions(widget, d);
}

app.registerExtension({
  name: "sg.pickers",

  async beforeRegisterNodeDef(nodeType, nodeData) {
    if (nodeData.name === "SGLoadVersion") return loadPickers(nodeType, nodeData);
    if (nodeData.name === "SGPublishVersion") return publishPickers(nodeType, nodeData);
  },
});

// Publish node. The panel is the point: a publish is remote and irreversible, so everything the run
// would do is on screen before it does it — the name it would create, where that lands, and every
// provenance concept beside the field it will be written to.
function publishPickers(nodeType, nodeData) {
  // The declared widgets, in INPUT_TYPES order, read from the definition the server just sent
  // rather than repeated here. This is the order a saved graph's widgets_values is in.
  restoreDeclaredWidgets(nodeType, declaredWidgets(nodeData));

  const onCreated = nodeType.prototype.onNodeCreated;
  nodeType.prototype.onNodeCreated = function () {
    onCreated?.apply(this, arguments);
    const node = this;

    if (!requireVueNodes(this)) return;

    const w = (n) => this.widgets?.find((x) => x.name === n);
    const project = w("project"), link = w("link"), task = w("task"), status = w("status");

    const state = { projectId: 0, projects: [], linkIds: {} };
    let statusMeta = {};
    let linkType = "Shot";   // per project, from /sg/profile; never assumed (probe 005)
    // A picked label carries its own type; `linkType` is only the fallback for one that does not.
    const typeOf = (label) => typeFromLabel(label) || linkType;

    const relayout = () => fitNode(this);

    textRows(w("note"), 5);   // prose, not a name

    const panel = addPanel(this, "SG Publish", relayout);
    // The status the operator picked, drawn the way SG draws it (probe 010).
    const statusOf = (label) => statusMeta[bare(label)] || null;

    // Every preview is numbered and only the newest may write: there are two round trips per
    // preview, so a widget changed twice quickly could answer out of order and leave the panel
    // describing the older graph.
    let previewing = 0;
    // The latest Version on this link and the files it wrote, as links. Built from whatever carries
    // {id, site_url, files} — the preview's `latest` before a run, the executed payload after one.
    // A `%04d` pattern is not a file, so its link opens the containing folder.
    const runFacts = (r) => !r || !r.id ? [] : [
      ...(r.site_url ? [{ label: "latest", value: `${r.code || "Version " + r.id}`,
                          href: `${r.site_url}/detail/Version/${r.id}` }] : []),
      ...(r.files || []).map((f) => ({
        label: f.kind === "frames" ? `${f.count} frame${f.count === 1 ? "" : "s"}` : f.kind,
        value: f.path,
        href: "file://" + f.path.replace(/[^/]*$/, ""),
      })),
    ];

    // `keepLog` is what the redraw after a run passes: the readout ahead of it changes, and the
    // lines that run wrote stay under it until the next Run or the next edit.
    const preview = async (keepLog = false) => {
      const mine = ++previewing;
      panel.loading();
      const q = new URLSearchParams({
        project: project?.value || "", link: bare(link?.value), task: bare(task?.value),
        code_template: w("code_template")?.value || "",
        root_name: w("root_name")?.value || "",
      });
      const d = await call(`/sg/preview_code?${q}`);
      if (mine !== previewing) return;
      if (!keepLog) panel.clearLog();
      if (!d.code) {
        panel.show({ error: d.error || "Version name produced nothing. Edit version name on this "
          + "node, or empty it to use the default under Settings, then SG." });
        return;
      }
      // Provenance lives in the executing graph, so hand over the very thing Run would send.
      let extra = {};
      try {
        const { output } = await app.graphToPrompt();
        extra = await call("/sg/preview_publish",
                           { body: { prompt: output, node_id: String(node.id) } });
      } catch (e) { /* an unbuilt graph simply has nothing to describe yet */ }
      if (mine !== previewing) return;
      // Its `error` is kept out of the spread on purpose: an `error` anywhere in what show() is
      // given replaces the whole readout, and the name must not be lost because the provenance call
      // failed. It becomes the line under the name instead.
      const { error, ...rest } = extra || {};
      const missing = (rest.missing_fields || []).length;
      // Which row of the truth table this node is on, in front of the operator rather than in the
      // fold: one run is one Version, and what that Version carries is decided by what is wired.
      // An empty root name or version name is named by Settings, and this is where the operator
      // sees what that resolves to.
      const facts = (d.templates || []).map((t) => ({ label: t.label, value: `${t.value} · ${t.source}` }))
        .concat(rest.media ? [{ label: "media", value: rest.media }] : [])
        .concat(runFacts(d.latest));
      panel.show({
        ...rest, facts,
        id: -1, code: d.code, task: d.task,
        // preview_code answers with the type it would use even when nothing is picked, so an unset
        // link would otherwise read as a bare "Shot" that had been decided.
        link: bare(link?.value) ? d.link : "",
        status: statusOf(status?.value),
        // What stops this Run: a name that cannot be written, or files that cannot land. Never
        // folded — the name is the readout, and neither of these is about the name.
        alert: d.alert || rest.alert || "",
        // The reason lives in the fold, so the pill carries it: a publish that cannot read its
        // provenance, or that would drop a mapped value, is not VALID however good the name is.
        state: (error || missing || d.alert || rest.alert) ? "warn" : "ok",
        why: error ? `Provenance could not be read. ${error}`
          : missing ? `${missing} field(s) below are missing from this site, struck through.`
          : "This is what the next Run will create.",
      });
    };
    // A typed widget is debounced, because every keystroke costs a graphToPrompt and two requests.
    // A combo is a decision, and answers at once.
    let pending;
    const previewSoon = () => { clearTimeout(pending); pending = setTimeout(preview, 250); };

    // ComfyUI skips a node whose inputs did not change and keeps its last result, which is the
    // rule that stops a re-run from filing duplicate Versions. Said on the panel, because the
    // readout above it names the NEXT version and a silent skip reads as a publish that failed.
    // ComfyUI announces the cached nodes first, then replays each one's old result as `executed`,
    // so the flag is read there and the sentence lands after the readout it explains.
    let cached = false;
    // Every listener is dropped when the node goes: a workflow opened and closed otherwise leaves
    // its listeners behind, and each later run redraws a panel that is on no screen.
    const listen = (name, fn) => {
      app.api.addEventListener(name, fn);
      const prev = node.onRemoved;
      node.onRemoved = function () {
        app.api.removeEventListener(name, fn);
        return prev?.apply(this, arguments);
      };
    };
    listen("execution_start", () => { cached = false; panel.clearLog(); });
    listen("execution_cached", ({ detail }) => {
      cached = (detail.nodes || []).map(String).includes(String(node.id));
    });
    listen("executed", ({ detail }) => {
      if (String(detail.node) !== String(node.id)) return;
      const rows = (detail.output && detail.output.published) || [];
      panel.clearLog();
      if (rows.length && cached) {
        panel.show({ id: rows[0].id, code: rows[0].code, link: rows[0].link,
                     status: statusOf(status?.value), state: "warn", why: "" });
        panel.log(`Not published again: nothing changed since ${rows[0].code}. Change the image `
          + "or a field on this node, then Run, for the next version.", false);
        return;
      }
      if (rows.length) {
        panel.show({
          id: rows[0].id, code: rows[0].code, link: rows[0].link,
          status: statusOf(status?.value), state: "ok",
          why: "",
          // `facts`, not `echo`: what a run actually wrote is nowhere else on the node. `media`
          // names the path the run took — the source file uploaded untouched, a ComfyUI encode, or
          // our own still — with the frame count measured off the clip itself.
          facts: [
            ...(rows[0].media ? [{ label: "media", value: rows[0].media }] : []),
            ...(rows[0].outputs && rows[0].outputs.length
              ? [{ label: "wrote", value: rows[0].outputs.join(", ") }] : []),
            ...runFacts(rows[0]),
          ],
        });
      }
      const text = (detail.output && detail.output.text) || [];
      if (text.length) panel.log(text, rows.length > 0);
      // What the NEXT run would create, now that this one has taken a number. The lines this run
      // wrote are the Version id and the paths it landed on, so they stay on the panel.
      setTimeout(() => preview(true), 1200);
    });
    if (!project || !link) return;

    // No onPick on the project: the widget's own callback is wrapped below and searchPicker fires
    // it, so asking here as well would load the project twice.
    const projectPick = projectPicker(this, project, state);
    const linkPick = linkPicker(this, link, state, {
      empty: "No link on this project matches those words.",
    });

    // Picking a second project supersedes every read the first one started: one cascade at a time,
    // and each step of it carries the token the entry point began with.
    const chain = cascade();
    // A site that answered with a sentence instead of rows stops the cascade there: every widget
    // keeps the value the saved graph gave it, and the sentence is on the panel.
    const stop = (msg) => { if (msg) panel.show({ error: msg }); return !!msg; };

    const loadTasks = async (picked, tok = chain.begin()) => {
      // The picked value, not the widget's: a widget's own .value is not always assigned yet when
      // its callback fires, and reading it here asks about the PREVIOUS link.
      const chosen = picked ?? link.value;
      const bad = await loadTaskOptions(task, typeOf(chosen), state.linkIds[chosen], tok);
      if (!tok.live || stop(bad)) return;
      await preview();
    };

    const loadLinks = async (tok = chain.begin()) => {
      const bad = await loadLinkOptions(link, state, tok);
      if (!tok.live || stop(bad)) return;
      linkPick.refresh();
      await loadTasks(undefined, tok);
    };

    const loadProject = async (picked, tok = chain.begin()) => {
      const bad = await selectProject(project, state, picked, tok);
      if (!tok.live || stop(bad)) return;
      // Per project, because one show hangs Versions off Shots and the next off Assets.
      const prof = await call(`/sg/profile?project_id=${state.projectId}`, tok);
      if (!tok.live || stop(prof.error)) return;
      linkType = prof.link_type || "Shot";
      if (status) {
        const s = await call(`/sg/statuses?project_id=${state.projectId}`, tok);
        if (!tok.live || stop(setOptions(status, s))) return;
        statusMeta = Object.fromEntries((s.items || []).map((x) => [x.label, x]));
      }
      projectPick.refresh(currentProject(project, state));
      await loadLinks(tok);
    };

    wrap(project, loadProject);
    wrap(link, loadTasks);
    // Everything the readout depends on. Nothing here is ever written back by preview(), which is
    // what keeps this from becoming a resolve loop.
    ["task", "status", "attach_workflow", "register_files"].forEach((n) =>
      wrap(w(n), () => preview()));
    ["code_template", "root_name", "note", "source_versions", "colour_space"].forEach((n) =>
      wrap(w(n), previewSoon));

    // domRow marks every row we add; a button is the one widget litegraph never marks itself, and
    // an injected widget that serializes shifts every declared value after it. The callback takes
    // no arguments: litegraph hands a button's callback the canvas and the node, and the cascade
    // token is the second parameter.
    dontSerialize(this.addWidget("button", "Sync from SG", null, () => loadProject()));
    // The Settings values written into the widgets, as a starting point to edit or to bring an
    // older node up to date. An emptied root name or version name follows Settings again.
    const copyDefaults = async () => {
      const d = await call(`/sg/node_defaults?project=${encodeURIComponent(project?.value || "")}`);
      if (d.error) { panel.show({ error: d.error }); return; }
      for (const [name, value] of Object.entries(d)) {
        const widget = w(name);
        if (!widget) continue;
        widget.value = widget.options?.values && !widget.options.values.includes(value)
          ? widget.options.values[0] : value;
      }
      relayout();
      preview();
    };
    dontSerialize(this.addWidget("button", "Fill from SG defaults", null, copyDefaults));
    // Who this publishes as is set under Settings, and a change there changes what every picker
    // reads (probe 027), so the node reloads.
    onSession(this, () => loadProject());
    loadProject();
  };
}

// Load node. The inputs are a rule, not an id, so the panel shows which Version the rule lands on
// and what made it — resolved by the node's own code, so the preview cannot disagree with the run.
function loadPickers(nodeType, nodeData) {
  restoreDeclaredWidgets(nodeType, declaredWidgets(nodeData));
  const onCreated = nodeType.prototype.onNodeCreated;
  nodeType.prototype.onNodeCreated = function () {
    onCreated?.apply(this, arguments);

    if (!requireVueNodes(this)) return;

    const w = (n) => this.widgets?.find((x) => x.name === n);
    const project = w("project"), link = w("link"), task = w("task");
    const source = w("source"), statuses = w("statuses");
    if (!project || !link) return;

    // Wide enough for `label | control` plus the readout's two columns: the stock 210px default puts
    // every provenance label on its own wrapped line.
    if (this.size[0] < 380) this.size[0] = 380;
    // The filter box holds a dozen lines of JSON, and the stock floor shows three. Anything longer
    // still scrolls, which is the frontend's own answer.
    textRows(w("filters"), 10);

    const state = { projectId: 0, projects: [], linkIds: {} };
    const relayout = () => fitNode(this);

    const projectPick = projectPicker(this, project, state, (it) => loadProject(it.value));
    const linkPick = linkPicker(this, link, state, {
      empty: "No link on this project matches those words.",
      onPick: () => loadTasks(),
    });
    hideWidget(statuses);
    const statusChips = statuses && chipSelect(this, statuses, {
      label: "statuses",
      empty: "This project has no statuses.",
      load: async () => (await call(`/sg/statuses?project_id=${state.projectId}`)).items || [],
    });

    const panel = addPanel(this, "SG Load", relayout);

    // Every resolve is numbered, and only the newest may write: two requests are in flight whenever
    // a widget is changed twice quickly, they can come back in either order, and the panel would
    // otherwise flicker through stale states before settling.
    let resolving = 0;
    // The last answer from /sg/resolve, kept so the frame widgets can redraw the readout without
    // asking the site again: the range came off disk once, and which slice of it to take is
    // arithmetic.
    let resolved = null;

    const draw = () => {
      if (!resolved) return;
      panel.show({
        ...resolved,
        // What the two frame widgets are asking for, so the frames row says what WILL be read
        // rather than only what exists.
        frame_ask: Number(w("frame")?.value || 0),
        count_ask: Number(w("frame_count")?.value ?? 0),
        // An escape hatch that is switched on must say so: a pinned id ignores the whole rule.
        // `extra filters` narrows rather than replaces, so it is not an override and says nothing.
        alert: resolved.alert || (resolved.pinned
          ? `Pinned to Version ${resolved.pinned}. All the fields above are ignored.` : ""),
      });
    };

    const refresh = async (over = {}) => {
      const mine = ++resolving;
      // `over` carries the value the callback was handed: a widget's own .value is not always
      // assigned yet when its callback fires, so reading it here asks about the PREVIOUS pick.
      const val = (n) => (n in over ? over[n] : w(n)?.value);
      const q = new URLSearchParams({
        project_id: state.projectId, project: project.value || "",
        link: bare(link.value), task: bare(val("task")),
        name_contains: val("name_contains") || "",
        newest_by: val("newest_by") || "",
        pin_version_id: val("pin_version_id") || 0,
        // Which source, so the readout answers for the file that will be read rather than for the
        // Version as a whole: two PublishedFiles on one Version can declare different colour spaces.
        source: val("source") || "auto",
        // String(): a graph saved before this widget moved can land a number here, and a raw
        // .trim() on it takes the whole picker down.
        filters: String(val("filters") ?? ""),
      });
      for (const s of String(val("statuses") || "").split(",")) {
        const t = s.trim();
        if (t) q.append("statuses", t);
      }
      panel.loading();
      const d = await call(`/sg/resolve?${q}`);
      if (mine !== resolving) return;      // superseded while we waited
      const pinned = Number(val("pin_version_id") || 0);
      resolved = { ...d, pinned };
      draw();
      if (source) {
        source.options.values = ["auto"].concat(d.media || []);
        // A saved value the site no longer offers falls back to `auto` rather than staying as a
        // combo entry the editor cannot draw. A PublishedFile key carries its type and filename, so
        // a file that was renamed or re-typed stops matching — which is the honest outcome, since
        // the node would otherwise guess which of several files the old label meant.
        if (!source.options.values.includes(source.value)) source.value = "auto";
      }
      app.graph.setDirtyCanvas(true, true);
    };

    // Picking a second project supersedes every read the first one started: one cascade at a time,
    // and each step of it carries the token the entry point began with.
    const chain = cascade();
    // A site that answered with a sentence instead of rows stops the cascade there: every widget
    // keeps the value the saved graph gave it, and the sentence is on the panel.
    const stop = (msg) => { if (msg) panel.show({ error: msg }); return !!msg; };

    const loadTasks = async (picked, tok = chain.begin()) => {
      const chosen = picked ?? link.value;
      const bad = await loadTaskOptions(task, typeFromLabel(chosen), state.linkIds[chosen], tok);
      if (!tok.live || stop(bad)) return;
      await refresh();
    };

    const loadLinks = async (tok = chain.begin()) => {
      const bad = await loadLinkOptions(link, state, tok);
      if (!tok.live || stop(bad)) return;
      linkPick.refresh();
      await loadTasks(undefined, tok);
    };

    const loadProject = async (picked, tok = chain.begin()) => {
      const bad = await selectProject(project, state, picked, tok);
      if (!tok.live || stop(bad)) return;
      projectPick.refresh(currentProject(project, state));
      statusChips?.reload();
      await loadLinks(tok);
    };

    wrap(project, loadProject);
    wrap(link, loadTasks);
    // `source` is in this list because which file is read changes the type, the count and the
    // declared colour space the readout shows.
    ["task", "name_contains", "statuses", "newest_by", "pin_version_id", "source"].forEach((n) =>
      wrap(w(n), (value) => refresh({ [n]: value })));
    // `frame` and `frame_count` redraw and do not re-resolve: where in a sequence to start does not
    // change what resolved, only which frames the readout says will be read.
    ["frame", "frame_count"].forEach((n) => wrap(w(n), draw));
    // `filters` holds the operator's OWN conditions, ANDed onto the fields server-side. Nothing
    // writes it, so it drives a refresh like any other field; debounced, because it is typed.
    let typing;
    wrap(w("filters"), (value) => {
      clearTimeout(typing);
      typing = setTimeout(() => refresh({ filters: value }), 400);
    });

    dontSerialize(this.addWidget("button", "Sync from SG", null, () => loadProject()));
    onSession(this, () => loadProject());
    loadProject();
  };
}
